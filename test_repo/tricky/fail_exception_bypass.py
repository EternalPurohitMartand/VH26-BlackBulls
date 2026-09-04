def exception_leak():
    f = open("dummy.txt", "w")
    try:
        f.write("Doing some risky operations...")
        raise ValueError("Something went wrong!")
        # Because the close is here instead of in a 'finally' block, 
        # the exception bypasses it. The analyzer must catch this.
        f.close()
    except ValueError:
        print("Caught an error")