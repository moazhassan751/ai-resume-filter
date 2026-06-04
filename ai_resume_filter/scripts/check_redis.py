import socket
s=socket.socket()
try:
    s.settimeout(1)
    s.connect(('127.0.0.1', 6379))
    print('redis: open')
except Exception as e:
    print('redis: closed', e)
finally:
    s.close()
