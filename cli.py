import argparse
import sys
import os
from analyzer.checker import analyze_file

def main():
    parser = argparse.ArgumentParser(description="LeakGuard AST Analyzer")
    parser.add_argument("target_directory", default=".", nargs="?", help="Directory to scan for Python files")
    args = parser.parse_args()

    target_dir = args.target_directory
    if not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)

    total_leaks = 0

    # Recursively find all .py files
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                leaks = analyze_file(filepath)
                
                # Format output for GitHub Actions annotations
                for leak in leaks:
                    print(f"::error file={leak['file_name']},line={leak['line_number']}::Resource '{leak['resource_name']}' leaked ({leak['leak_type']}).")
                    total_leaks += 1

    # Exit with 1 if leaks are found to fail the CI build
    if total_leaks > 0:
        sys.exit(1)
    else:
        print("No resource leaks detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()