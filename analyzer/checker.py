# analyzer/checker.py
import ast
from typing import List, Dict, Any

RESOURCE_OPENERS = {
    ('open',), ('os', 'open'), ('io', 'open'),
    ('connect',), ('socket', 'connect'),
    ('socket', 'socket'),
    ('sqlite3', 'connect'),
    ('subprocess', 'Popen'),
}

def _is_resource_opener(call_node: ast.Call) -> bool:
    func = call_node.func
    if isinstance(func, ast.Name):
        return (func.id,) in RESOURCE_OPENERS
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return (func.value.id, func.attr) in RESOURCE_OPENERS
    return False

def _get_with_bound_names(with_node: ast.With) -> List[str]:
    names = []
    for item in with_node.items:
        if item.optional_vars:
            if isinstance(item.optional_vars, ast.Name):
                names.append(item.optional_vars.id)
            elif isinstance(item.optional_vars, ast.Tuple):
                for elt in item.optional_vars.elts:
                    if isinstance(elt, ast.Name):
                        names.append(elt.id)
    return names

class LeakVisitor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.leaks: List[Dict[str, Any]] = []
        self.resources: Dict[str, Dict[str, Any]] = {}
        self._in_try_finally = False
        self._unreachable = False

    def record_finding(self, line_number: int, var_name: str, leak_type: str, status: str = "LEAK"):
        for existing in self.leaks:
            if existing['resource_name'] == var_name and existing['status'] == status:
                return
        self.leaks.append({
            "file_name": self.filename,
            "line_number": line_number,
            "resource_name": var_name,
            "leak_type": leak_type,
            "status": status
        })

    def visit_FunctionDef(self, node):
        old_resources = self.resources.copy()
        self.resources = {}
        self._unreachable = False
        self.generic_visit(node)
        for var, state in self.resources.items():
            if state['status'] == 'OPEN':
                self.record_finding(state['line'], var, "Missing close", status="LEAK")
            elif state['status'] == 'UNCERTAIN':
                self.record_finding(state['line'], var, "Cross-function handoff", status="UNCERTAIN")
        self.resources = old_resources

    def visit_With(self, node):
        for name in _get_with_bound_names(node):
            self.resources[name] = {'line': node.lineno, 'status': 'CLOSED'}
        self.generic_visit(node)

    def visit_Try(self, node):
        for body_node in node.body:
            self.visit(body_node)

        close_calls_in_finally = set()
        if node.finalbody:
            saved = self._in_try_finally
            self._in_try_finally = True
            for finally_node in node.finalbody:
                self.visit(finally_node)
            self._in_try_finally = saved

            for finally_node in node.finalbody:
                for n in ast.walk(finally_node):
                    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                            and n.func.attr == 'close' and isinstance(n.func.value, ast.Name)):
                        close_calls_in_finally.add(n.func.value.id)

            for var_name in close_calls_in_finally:
                if var_name in self.resources and self.resources[var_name]['status'] in ['OPEN', 'UNCERTAIN']:
                    self.resources[var_name]['status'] = 'CLOSED'

        for handler in node.handlers:
            self.visit(handler)

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call) and _is_resource_opener(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in self.resources and self.resources[target.id]['status'] == 'OPEN':
                        self.record_finding(node.lineno, target.id, "Reassigned before close", status="LEAK")
                    self.resources[target.id] = {
                        'line': node.lineno,
                        'status': 'OPEN'
                    }
        self.generic_visit(node)

    def visit_If(self, node):
        snapshot = {v: s.copy() for v, s in self.resources.items()}
        closed_in_body = set()
        self.generic_visit(node)
        for v, s in self.resources.items():
            if v in snapshot and snapshot[v]['status'] != 'CLOSED' and s['status'] == 'CLOSED':
                closed_in_body.add(v)
        for v in closed_in_body:
            self.resources[v] = snapshot[v]

    def visit_Call(self, node):
        if not self._unreachable:
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'close' and isinstance(node.func.value, ast.Name):
                    var_name = node.func.value.id
                    if var_name in self.resources and self.resources[var_name]['status'] in ['OPEN', 'UNCERTAIN']:
                        self.resources[var_name]['status'] = 'CLOSED'

            for arg in node.args:
                if isinstance(arg, ast.Name):
                    var_name = arg.id
                    if var_name in self.resources and self.resources[var_name]['status'] == 'OPEN':
                        if self._in_try_finally:
                            self.resources[var_name]['status'] = 'CLOSED'
                        else:
                            self.resources[var_name]['status'] = 'UNCERTAIN'

        self.generic_visit(node)

    def check_control_flow_leak(self, node, flow_type: str):
        if self._in_try_finally:
            return
        for var, state in self.resources.items():
            if state['status'] == 'OPEN':
                self.record_finding(node.lineno, var, f"{flow_type} bypass", status="LEAK")

    def visit_Return(self, node):
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in self.resources and self.resources[var_name]['status'] == 'OPEN':
                self.resources[var_name]['status'] = 'UNCERTAIN'
        self.check_control_flow_leak(node, "Early return")
        self._unreachable = True
        self.generic_visit(node)

    def visit_Raise(self, node):
        self.check_control_flow_leak(node, "Exception")
        self._unreachable = True
        self.generic_visit(node)

    def visit_Break(self, node):
        self.check_control_flow_leak(node, "Loop break")
        self.generic_visit(node)

    def visit_Continue(self, node):
        self.check_control_flow_leak(node, "Loop continue")
        self.generic_visit(node)

def analyze_file(filepath: str) -> List[Dict[str, Any]]:
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source, filename=filepath)
    visitor = LeakVisitor(filepath)
    visitor.visit(tree)
    return visitor.leaks