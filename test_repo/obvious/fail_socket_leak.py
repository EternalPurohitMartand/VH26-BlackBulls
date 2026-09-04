def socket_leak():
    """Socket opened but never closed. Tests non-file resource detection."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("example.com", 80))
    s.send(b"GET / HTTP/1.0\r\nHost: example.com\r\n\r\n")
    data = s.recv(1024)
    return data
