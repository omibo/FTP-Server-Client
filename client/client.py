import socket, time, logging

HOST = '0.0.0.0'  # The server's hostname or IP address
PORT = 8000        # The port used by the server


# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#     s.connect((HOST, PORT))
#     while True:
#         print(s.recv(1024))
#         s.send(input().encode())

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

print(s.recv(1024))
command = input()
s.send(command.encode())
print(s.recv(1024))
command = input()
s.send(command.encode())
print(s.recv(1024))

command = input()
s.send(command.encode())

logging.info("TEST CLIENT")

s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s1.connect((HOST, 8001))
i = 0
while True:
    d = s1.recv(1024)
    print(d)
    if len(d) < 2:
        break
    i += 1

s1.close()
print(s.recv(1024))
logging.info("CLOSING COMMAND SOCKET CLIENT")
s.close()

