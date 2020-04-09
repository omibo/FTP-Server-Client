import constants
from utils import util

from threading import Thread
import socket, time


class Client(Thread):
    def __init__(self, configs):
        Thread.__init__(self)
        self.serverCommandAddress = (constants.SERVER_IP_ADDRESS, configs['commandChannelPort'])
        self.serverDataAddress = (constants.SERVER_IP_ADDRESS, configs['dataChannelPort'])

        self.clientUp = True

        self.commandSock = None
        self.dataSock = None

    def setCommandSocket(self):
        self.commandSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.commandSock.connect(self.serverCommandAddress)
        print(self.commandSock.recv(constants.RECV_LENGTH))

    def setDataSocket(self):
        self.dataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dataSock.connect(self.serverDataAddress)

    def run(self):
        while self.clientUp:
            commandStr = input()
            command = commandStr.split()
            if command[0] == 'LIST':
                self.listCommand(commandStr)
            elif command[0] == 'DL':
                self.downloadCommand(commandStr)
            elif commandStr == 'Q':
                self.close()
                self.stop()
            else:
                self.justCommandChannel(commandStr)

    def justCommandChannel(self, commandStr):
        self.commandSock.send(commandStr.encode())
        print(self.commandSock.recv(constants.RECV_LENGTH).decode())

    def listCommand(self, commandStr):
        self.commandSock.send(commandStr.encode())
        self.setDataSocket()
        print("FILES IN YOR WORKING DIRECTORY")
        while True:
            data = self.dataSock.recv(constants.RECV_LENGTH).decode()
            if not data:
                break
            print(data)
        print(self.commandSock.recv(constants.RECV_LENGTH).decode())
        self.dataSock.close()

    def downloadCommand(self, commandStr):
        self.commandSock.send(commandStr.encode())
        self.setDataSocket()
        fileLength = int(self.dataSock.recv(constants.RECV_LENGTH).decode())
        while True:
            data = self.dataSock.recv(constants.RECV_LENGTH).decode()
            if not data:
                break
            print(data)
        print(self.commandSock.recv(constants.RECV_LENGTH).decode())
        self.dataSock.close()

    def close(self):
        self.commandSock.close()
        self.dataSock.close()

    def stop(self):
        self.clientUp = False




# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#     s.connect((HOST, PORT))
#     while True:
#         print(s.recv(1024))
#         s.send(input().encode())

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.connect((HOST, PORT))
#
# print(s.recv(1024))
# command = input()
# s.send(command.encode())
# print(s.recv(1024))
# command = input()
# s.send(command.encode())
# print(s.recv(1024))
#
# command = input()
# s.send(command.encode())
#
# s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s1.connect((HOST, 8001))
# length = s1.recv(1024).decode()
# print(length)
# while True:
#     data = s1.recv(1024)
#     print(data.decode())
#     if not data:
#         break
#
# print("JKKJKJKJKJKJKJK")
# s1.close()
# print(s.recv(1024))
# logging.info("CLOSING COMMAND SOCKET CLIENT")
# s.close()

if __name__ == '__main__':
    configs = util.getConfigs()
    client = Client(configs)
    client.setCommandSocket()
    client.start()
    if not client.clientUp:
        client.join()
