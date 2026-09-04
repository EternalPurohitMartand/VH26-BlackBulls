def safe_with_text_close():
    """Has .close() text in a comment/string, but never actually closes the file.
    A regex/pattern matcher would flag this. AST analysis correctly ignores it."""
    f = open("data.txt", "r")
    data = f.read()
    # TODO: f.close() - add this before shipping
    msg = "Remember to call f.close() on the file handle"
    print(msg)
    return data
