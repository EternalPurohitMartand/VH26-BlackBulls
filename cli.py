# cli.py
import sys
import os
from analyzer.checker import analyze_file

def run_benchmark():
    test_dir = "test_repo"
    if not os.path.exists(test_dir):
        print(f"Error: '{test_dir}' folder not found for benchmarking.")
        sys.exit(1)

    total_files = 0
    tp = 0  # leak files correctly detected
    fn = 0  # leak files missed
    fp = 0  # safe files wrongly flagged
    tn = 0  # safe files correctly passed

    for root, _, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py'):
                total_files += 1
                filepath = os.path.join(root, file)
                leaks = analyze_file(filepath)
                has_leak = any(l.get('status') == 'LEAK' for l in leaks)

                is_leak_file = ("obvious" in root or "tricky" in root) and "uncertain" not in file

                if is_leak_file:
                    if has_leak:
                        tp += 1
                    else:
                        fn += 1
                else:
                    if has_leak:
                        fp += 1
                    else:
                        tn += 1

    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print("\n" + "╭" + "─" * 36 + "╮")
    print("│         LEAKGUARD BENCHMARK          │")
    print("╰" + "─" * 36 + "╯")
    print(f"Files scanned:            {total_files}")
    print(f"True Positives (TP):      {tp}")
    print(f"False Negatives (FN):     {fn}")
    print(f"False Positives (FP):     {fp}")
    print(f"True Negatives (TN):      {tn}")
    print("-" * 38)
    print(f"Precision:                {precision:.1f}%")
    print(f"Recall:                   {recall:.1f}%")
    print(f"F1 Score:                 {f1:.1f}%")
    print("=" * 38)
    sys.exit(0)

def apply_patch(leak):
    """Uses GenAI to intelligently refactor the leaking file, falling back to clean line insertion with proper indentation if needed."""
    try:
        from ml_pipeline.genai_patcher import generate_safe_code
    except ImportError:
        print("\n❌ google-genai package not installed. Run: pip install google-genai")
        return

    filepath = leak['file_name']
    var_name = leak['resource_name']
    line_num = leak['line_number']
    
    print(f"\n  🤖 Triggering GenAI Auto-Refactor for {filepath}...")
    safe_code = generate_safe_code(filepath, line_num, var_name)
    
    if safe_code:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(safe_code)
        print("  ✅ GenAI successfully refactored and patched the file!\n")
    else:
        print("  ⚠️ GenAI patch skipped. Applying fallback .close() injection...")
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Get the exact indentation of the line where the resource was opened
        open_line = lines[line_num - 1]
        indentation = len(open_line) - len(open_line.lstrip())
        indent_str = " " * indentation
        
        # Format the patch with matching indentation and insert it cleanly
        patch_line = f"{indent_str}{var_name}.close()  # [LeakGuard Auto-Patch]\n"
        lines.insert(line_num, patch_line)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print("  ✅ Fallback patch applied successfully with correct indentation!\n")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cli.py <target_directory> [--strict] [--fix] [--yes]")
        print("  python cli.py benchmark")
        sys.exit(1)

    if sys.argv[1] == "benchmark":
        run_benchmark()

    target_dir = sys.argv[1]
    strict_mode = "--strict" in sys.argv
    fix_mode = "--fix" in sys.argv
    auto_yes = "--yes" in sys.argv

    total_files = 0
    definite_leaks = 0
    uncertain_count = 0
    fixed_count = 0
    auto_fix_all = auto_yes

    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' not found.")
        sys.exit(1)

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.py'):
                total_files += 1
                filepath = os.path.join(root, file)
                file_leaks = analyze_file(filepath)
                if file_leaks:
                    for leak in file_leaks:
                        if leak.get('status', 'LEAK') == 'UNCERTAIN':
                            uncertain_count += 1
                            try:
                                from ml_pipeline.predictor import get_leak_confidence
                                confidence = get_leak_confidence(filepath)
                            except ImportError:
                                confidence = None
                            
                            if confidence is not None:
                                print(f"⚠️  WARNING file={leak['file_name']},line={leak['line_number']}::Resource '{leak['resource_name']}' ownership uncertain. ML Leak Risk: {confidence:.1f}%")
                            else:
                                print(f"⚠️  WARNING file={leak['file_name']},line={leak['line_number']}::Resource '{leak['resource_name']}' ownership uncertain ({leak['leak_type']}).")
                            
                            if strict_mode:
                                definite_leaks += 1
                        else:
                            definite_leaks += 1
                            print(f"::error file={leak['file_name']},line={leak['line_number']}::Resource '{leak['resource_name']}' leaked ({leak['leak_type']}).")
                            
                            # INTERACTIVE AUTO-FIX PROMPT WITH 'ALL' OPTION
                            if fix_mode:
                                print(f"\n  💡 Auto-Fix available for {leak['file_name']} (Line {leak['line_number']})")
                                
                                if auto_fix_all:
                                    choice = 'y'
                                else:
                                    choice = input(f"  ❓ Apply patch to safely close '{leak['resource_name']}'? [y/N/a (all)]: ").strip().lower()
                                    if choice == 'a':
                                        auto_fix_all = True
                                        choice = 'y'
                                
                                if choice == 'y':
                                    apply_patch(leak)
                                    print("  ✅ Patch applied successfully!\n")
                                    fixed_count += 1
                                    definite_leaks -= 1  # Remove from blocker count since we fixed it

    print("\n" + "=" * 42)
    print("              LEAKGUARD REPORT")
    print("=" * 42)
    print(f"Files scanned:             {total_files}")
    print(f"Definite leaks found:      {definite_leaks + fixed_count}")
    print(f"Uncertain ownership:       {uncertain_count}")
    print(f"Patches applied:           {fixed_count}")
    print(f"Strict mode:               {'ENABLED' if strict_mode else 'DISABLED'}")
    print(f"Auto-Fix mode:             {'ENABLED' if fix_mode else 'DISABLED'}")
    print("-" * 42)

    if definite_leaks > 0:
        print("❌ CI STATUS: BLOCKED")
        print(f"\n{definite_leaks} unresolved resource violation(s) remaining.")
        print("=" * 42)
        sys.exit(1)
    else:
        print("✅ CI STATUS: PASSED")
        print("\nNo unresolved resource leaks detected.")
        print("=" * 42)
        sys.exit(0)

if __name__ == '__main__':
    main()