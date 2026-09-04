def conditional_close_leak():
    """Close only happens in one branch. If condition is False, resource leaks."""
    f = open("data.txt", "r")
    data = f.read()
    if data:
        f.close()
    return data
