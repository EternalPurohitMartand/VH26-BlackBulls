# analyzer/checker.py
import ast
from typing import List, Dict, Any

class LeakVisitor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.leaks: List[Dict[str, Any]] = []
        self.resources: Dict[str, Dict[str, Any]] = {}

    def record_finding(self, line_number: int, var_name: str, leak_type: str, status: str = "LEAK"):
        self.leaks.append({
            "file_name": self.filename,
            "line_number": line_number,
            "resource_name": var_name,
            "leak_type": leak_type,
            "status": status  # This MUST be "status" so cli.py can read it
        })

    def visit_FunctionDef(self, node):
        old_resources = self.resources.copy()
        self.resources = {}
        self.generic_visit(node)
        for var, state in self.resources.items():
            if state['status'] == 'OPEN':
                self.record_finding(state['line'], var, "Missing close", status="LEAK")
            elif state['status'] == 'UNCERTAIN':
                self.record_finding(state['line'], var, "Cross-function handoff", status="UNCERTAIN")
        self.resources = old_resources

    def visit_With(self, node):
        self.generic_visit(node)

    def visit_Try(self, node):
        for body_node in node.body:
            self.visit(body_node)
        if node.finalbody:
            for handler in node.finalbody:
                self.visit(handler)
        for handler in node.handlers:
            self.visit(handler)

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call):
            func = node.value.func
            is_target = False
            if isinstance(func, ast.Name) and func.id == 'open':
                is_target = True
            elif isinstance(func, ast.Attribute) and func.attr == 'connect':
                is_target = True

            if is_target:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.resources[target.id] = {
                            'line': node.lineno,
                            'status': 'OPEN'
                        }
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check if resource is being closed locally
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'close' and isinstance(node.func.value, ast.Name):
                var_name = node.func.value.id
                if var_name in self.resources and self.resources[var_name]['status'] in ['OPEN', 'UNCERTAIN']:
                    self.resources[var_name]['status'] = 'CLOSED'

        # Check if resource is passed as an argument to another function (ownership transfer boundary)
        for arg in node.args:
            if isinstance(arg, ast.Name):
                var_name = arg.id
                if var_name in self.resources and self.resources[var_name]['status'] == 'OPEN':
                    self.resources[var_name]['status'] = 'UNCERTAIN'

        self.generic_visit(node)

    def check_control_flow_leak(self, node, flow_type: str):
        for var, state in self.resources.items():
            if state['status'] == 'OPEN':
                self.record_finding(node.lineno, var, f"{flow_type} bypass", status="LEAK")

    def visit_Return(self, node):
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in self.resources and self.resources[var_name]['status'] == 'OPEN':
                self.resources[var_name]['status'] = 'UNCERTAIN'
        
        self.check_control_flow_leak(node, "Early return")
        self.generic_visit(node)

    def visit_Raise(self, node):
        self.check_control_flow_leak(node, "Exception")
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