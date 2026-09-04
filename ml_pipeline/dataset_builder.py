import ast
import os
import csv

class FeatureExtractionVisitor(ast.NodeVisitor):
    """Extracts numerical features from Python AST for Machine Learning."""
    def __init__(self):
        self.features = {
            "has_with_statement": 0,
            "has_try_finally": 0,
            "explicit_close_calls": 0,
            "returns_early": 0,
            "raises_exception": 0,
            "passed_to_function": 0
        }
        self.tracking_vars = set()

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', '') == 'open':
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.tracking_vars.add(target.id)
        self.generic_visit(node)

    def visit_With(self, node):
        self.features["has_with_statement"] = 1
        self.generic_visit(node)

    def visit_Try(self, node):
        if node.finalbody:
            self.features["has_try_finally"] = 1
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'close':
            if isinstance(node.func.value, ast.Name) and node.func.value.id in self.tracking_vars:
                self.features["explicit_close_calls"] += 1
        
        for arg in node.args:
            if isinstance(arg, ast.Name) and arg.id in self.tracking_vars:
                self.features["passed_to_function"] = 1
        self.generic_visit(node)

    def visit_Return(self, node):
        if self.tracking_vars:
            self.features["returns_early"] = 1
        self.generic_visit(node)

    def visit_Raise(self, node):
        if self.tracking_vars:
            self.features["raises_exception"] = 1
        self.generic_visit(node)

def build_dataset(test_dir="test_repo", output_file="ml_pipeline/dataset.csv"):
    """Scans the test_repo and builds a CSV dataset for ML training."""
    if not os.path.exists("ml_pipeline"):
        os.makedirs("ml_pipeline")
        
    dataset = []
    
    for root, _, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                visitor = FeatureExtractionVisitor()
                visitor.visit(tree)
                
                # Determine the true label based on the folder structure
                is_leak = 1 if "fail_" in file else 0
                
                row = {"file_name": file}
                row.update(visitor.features)
                row["is_leak"] = is_leak
                dataset.append(row)

    headers = ["file_name", "has_with_statement", "has_try_finally", "explicit_close_calls", "returns_early", "raises_exception", "passed_to_function", "is_leak"]
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(dataset)
        
    print(f"✅ Successfully extracted features from {len(dataset)} files.")
    print(f"📊 Dataset saved to {output_file}")

if __name__ == '__main__':
    build_dataset()