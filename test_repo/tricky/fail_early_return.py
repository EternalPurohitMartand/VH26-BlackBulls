def early_return_leak(condition):
    f = open("dummy.txt", "r")
    if condition:
        # The analyzer should catch that we returned before f.close() was reached.
        return "Aborted"
    
    data = f.read()
    f.close()
    return data