def reassign_leaks_original():
    """The original file handle is lost when reassigned. The close() only
    closes the second resource, not the first. AST analysis tracks each
    binding separately."""
    f = open("first.txt", "r")
    f = open("second.txt", "r")
    data = f.read()
    f.close()
    return data
