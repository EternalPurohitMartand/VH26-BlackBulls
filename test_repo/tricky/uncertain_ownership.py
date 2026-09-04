def external_handler(file_obj):
    # Dummy external handler function
    pass

def process_external_resource():
    f = open("data.txt", "r")
    # Passed to an external function. Analyzer cannot prove if it closes or leaks.
    external_handler(f)