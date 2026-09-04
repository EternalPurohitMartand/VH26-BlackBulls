def safe_try_finally():
    f = open("dummy.txt", "w")
    try:
        f.write("Safe execution")
    finally:
        # The analyzer should recognize this finally block guarantees cleanup
        f.close()