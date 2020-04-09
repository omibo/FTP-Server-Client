from server.connectionThread import SocketServerThread
from utils import util
import constants

from threading import Thread
import socket
import time
import logging
import sys


class SocketServer(Thread):

    def __init__(self, configs):
        Thread.__init__(self)
        self.commandSock = None
        self.dataSock = None
        self.commandAddress = (constants.SERVER_IP_ADDRESS, configs['commandChannelPort'])
        self.dataAddress = (constants.SERVER_IP_ADDRESS, configs['dataChannelPort'])
        self.connectionThreads = list()
        self.serverUp = True

    def setCommandSocket(self):
        self.commandSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.commandSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.commandSock.bind(self.commandAddress)
        self.commandSock.listen(constants.MAX_CLIENT_IN_QUEUE)

    def setDataSocket(self):
        self.dataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dataSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.dataSock.bind(self.dataAddress)
        self.dataSock.listen(constants.MAX_CLIENT_IN_QUEUE)

    def run(self):
        logging.info(f'SERVER START.    Command Address:{self.commandAddress}       Data Address:{self.dataAddress}')
        print(f'SERVER START.    Command Address:{self.commandAddress}       Data Address:{self.dataAddress}')

        while self.serverUp:
            clientSock, clientAddr = self.commandSock.accept()
            logging.info(f"Client with address {clientAddr} connect to server command address")
            print("Client with address ", clientAddr, " connect to server command address")
            clientThread = SocketServerThread(clientSock, clientAddr, self.dataSock, configs)
            self.connectionThreads.append(clientThread)
            clientThread.start()

        self.close()

    def close(self):
        logging.info('Close server and all clients connection')
        print('Close server and all clients connection')
        for thread in self.connectionThreads:
            thread.stop()
            thread.join()
        self.commandSock.close()
        self.dataSock.close()

    def stop(self):
        self.serverUp = False


def configLogging(loggingConfig):
    logging.basicConfig(filename=loggingConfig['path'], format='%(levelname)s: %(asctime)s %(message)s',level=logging.INFO)
    if not loggingConfig['enable']:
        logging.disable(sys.maxsize)


if __name__ == '__main__':
    configs = util.getConfigs()
    configLogging(configs['logging'])
    server = SocketServer(configs)
    server.setCommandSocket()
    server.setDataSocket()
    server.start()
    time.sleep(300)
    server.stop()
    server.join()
