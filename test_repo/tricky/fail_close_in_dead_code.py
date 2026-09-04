def looks_safe_but_leaks():
    """Has f.close() text, but it is UNREACHABLE code after raise.
    A pattern matcher sees 'f.close()' and thinks it is safe.
    AST analysis sees the close is dead code and flags the leak."""
    f = open("data.txt", "w")
    try:
        f.write("Critical data")
        raise RuntimeError("Simulated failure")
        f.close()
    except RuntimeError:
        print("Error occurred - close() was never reached")
