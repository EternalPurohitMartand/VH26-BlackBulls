# test_repo/pass_with_statement.py

def safe_file_read():
    # The 'with' context manager automatically closes the file.
    # The AST analyzer should ignore this and not flag a leak.
    with open("dummy.txt", "r") as f:
        data = f.read()
        print("Reading data...")
    return data