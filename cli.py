# cli.py
import sys
import os
from analyzer.checker import analyze_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python cli.py <target_directory>")
        sys.exit(1)

    target_dir = sys.argv[1]
    total_files = 0
    total_leaks = 0
    all_leaks = []

    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' not found.")
        sys.exit(1)

    # Walk through the target directory to find python files
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.py'):
                total_files += 1
                filepath = os.path.join(root, file)
                file_leaks = analyze_file(filepath)
                if file_leaks:
                    for leak in file_leaks:
                        all_leaks.append(leak)
                        total_leaks += 1
                        # Maintain GitHub Actions annotation format for CI/CD
                        print(f"::error file={leak['file_name']},line={leak['line_number']}::Resource '{leak['resource_name']}' leaked ({leak['leak_type']}).")

    # Print professional enterprise summary report
    print("\n" + "=" * 42)
    print("              LEAKGUARD REPORT")
    print("=" * 42)
    print(f"Files scanned:             {total_files}")
    print(f"Definite leaks found:      {total_leaks}")
    print("-" * 42)

    if total_leaks > 0:
        print("❌ CI STATUS: BLOCKED")
        print(f"\n{total_leaks} resource lifetime violation(s) found.")
        print("=" * 42)
        sys.exit(1)
    else:
        print("✅ CI STATUS: PASSED")
        print("\nNo resource leaks detected.")
        print("=" * 42)
        sys.exit(0)

if __name__ == '__main__':
    main()