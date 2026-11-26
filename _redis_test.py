import socket
s = socket.socket(); s.settimeout(3)
try:
    s.connect(("127.0.0.1", 6379))
    s.sendall(b"AUTH Edghh35676dffgfg454656dfdfghtdfd\r\nPING\r\n")
    print("YANIT:", s.recv(128))
except Exception as h:
    print("HATA:", h)