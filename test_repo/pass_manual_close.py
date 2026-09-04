def manual_safe_read():
    # The analyzer should see the open() and the close() and mark it safe.
    f = open("dummy.txt", "r")
    data = f.read()
    f.close()
    return data