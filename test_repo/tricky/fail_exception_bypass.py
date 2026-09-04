def exception_leak():
    f = open("dummy.txt", "w")
    try:
        f.write("Doing some risky operations...")
        raise ValueError("Something went wrong!")
        f.close()
    except ValueError:
        print("Caught an error")
