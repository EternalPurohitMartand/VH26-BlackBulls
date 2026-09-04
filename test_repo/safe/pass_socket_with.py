def safe_socket_with():
    """Socket used as context manager - safe, no leak."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("example.com", 80))
        s.send(b"GET / HTTP/1.0\r\nHost: example.com\r\n\r\n")
        data = s.recv(1024)
    return data
