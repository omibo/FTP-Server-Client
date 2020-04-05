from server.connectionThread import SocketServerThread
from utils import parseConfigFile
import constants

from threading import Thread
import socket
import time


class SocketServer(Thread):

    def __init__(self, configs):
        Thread.__init__(self)
        self.sock = None
        self.address = (constants.SERVER_IP_ADDRESS, configs['commandChannelPort'])
        self.dataPort = configs['dataChannelPort']
        self.connectionThreads = list()
        self.serverUp = True

    def setSocket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((constants.SERVER_IP_ADDRESS, self.address[1]))
        self.sock.listen(constants.MAX_CLIENT_IN_QUEUE)

    def run(self):
        print(f'Server start.       IP address:{constants.SERVER_IP_ADDRESS}      data port:{self.dataPort}'
              f'       command port{self.address[1]}')
        while self.serverUp:
            conn, clientAddr = self.sock.accept()
            clientThread = SocketServerThread(conn, clientAddr, self.dataPort)
            self.connectionThreads.append(clientThread)
            clientThread.start()

        self.close()

    def close(self):
        print('Close server and all clients connection')
        for thread in self.connectionThreads:
            thread.stop()
            thread.join()
        self.sock.close()

    def stop(self):
        self.serverUp = False


def main():
    configs = parseConfigFile.getConfigs()
    server = SocketServer(configs)
    server.setSocket()
    server.start()
    time.sleep(40)
    server.stop()
    server.join()
    print('End.')


main()