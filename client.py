from globals import constants
from utils import util

from threading import Thread
import os
import pickle
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
                self.justCommandChannel('QUIT')
                self.close()
                self.stop()
            elif commandStr == 'QUIT':
                self.justCommandChannel(commandStr)
                self.setCommandSocket()
            else:
                self.justCommandChannel(commandStr)

    def justCommandChannel(self, commandStr):
        self.commandSock.send(commandStr.encode())
        print(self.commandSock.recv(constants.RECV_LENGTH).decode())

    def listCommand(self, commandStr):
        self.commandSock.send(commandStr.encode())
        receiveMsg = self.commandSock.recv(constants.RECV_LENGTH).decode()
        if receiveMsg != constants.CLIENT_READY_TO_RECEIVE_LIST:
            print(receiveMsg)
            return
        self.setDataSocket()
        print("FILES IN YOR WORKING DIRECTORY")
        while True:
            data = self.dataSock.recv(constants.RECV_LENGTH)
            if not data:
                break
            print(pickle.loads(data))
        lists = self.commandSock.recv(constants.RECV_LENGTH).decode()
        for listItem in lists.split('-'):
            print(listItem)
        self.dataSock.close()

    def downloadCommand(self, commandStr):
        self.commandSock.send(commandStr.encode())
        commandAnswere = self.commandSock.recv(constants.RECV_LENGTH).decode()
        if not commandAnswere.isdigit():
            print(commandAnswere)
            return
        fileLength = int(commandAnswere)
        print("length of wanted file ", fileLength)
        self.commandSock.send(constants.CLIENT_AGREE_TO_DOWNLOAD_MSG.encode())
        length = 0
        self.setDataSocket()
        with open(os.path.join(os.getcwd() + '/clientFolder', commandStr.split()[1]), "w") as f:
            while length < fileLength:
                data = self.dataSock.recv(constants.RECV_LENGTH).decode()
                length += len(data)
                if not data:
                    break
                f.write(data)

        self.dataSock.close()
        if length != fileLength:
            self.commandSock.send(constants.CLIENT_DOWNLOAD_UNSUCCESSFUL.encode())
            print("Can't download file completely")
        else:
            self.commandSock.send(constants.CLIENT_DOWNLOAD_SUCCESSFULLY.encode())
            print(self.commandSock.recv(constants.RECV_LENGTH).decode())

    def close(self):
        self.commandSock.close()

    def stop(self):
        self.clientUp = False


if __name__ == '__main__':
    configs = util.getConfigs()
    client = Client(configs)
    client.setCommandSocket()
    client.start()
    if not client.clientUp:
        client.join()
