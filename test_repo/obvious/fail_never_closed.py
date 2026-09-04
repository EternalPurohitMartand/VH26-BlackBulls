# test_repo/fail_never_closed.py

def leaky_file_read():
    # The file is opened and assigned to 'f', but never closed.
    # The AST analyzer should catch this and the GitHub Action should fail (exit code 1).
    f = open("dummy.txt", "r")
    data = f.read()
    print("Reading data...")
    return data
    f.close()  # 🛠️ [LeakGuard Auto-Patch]

    f.close()  # [LeakGuard Auto-Patch]
