from constants import RECV_LENGTH, SEND_LENGTH
from server.user import User
from utils import util

from threading import Thread
from pathlib import Path
import socket
import shutil
import os
import time
import logging


class SocketServerThread(Thread):
    def __init__(self, clientSock, clientAddress, dataSock):
        Thread.__init__(self)
        self.commandSock = clientSock
        self.clientAddress = clientAddress
        self.dataSock = dataSock

        self.serverUp = True
        self.user = User()

    def userNotLoggedIn(self):
        self.commandSock.send(b"332 Need account for login.")
        logging.warning(f"Client {self.clientAddress} want PWD without login")

    def errorHappened(self, msg):
        self.commandSock.send(b"500 Error.")
        logging.error(msg)

    def run(self):
        self.commandSock.send(b"Hello. Server is waiting for you.")
        while self.serverUp:
            try:
                commandMsg = self.commandSock.recv(RECV_LENGTH).decode()
                if commandMsg == '':
                    self.stop()
                logging.info(f"command '{commandMsg}' received from client {self.clientAddress}")
            except socket.error as err:
                logging.error(f"Error happened in receiving command from client {self.clientAddress}")
                continue

            command = commandMsg.split()
            if util.validateCommand(command):
                method = getattr(self, command[0])
                method(command[1:])
            else:
                self.commandSock.send(b"501 Syntax error in parameters or arguments.")
                logging.warning(f"Bad command request by client {self.clientAddress}")
        self.close()

    def USER(self, args):
        user = util.findUser(args[0])
        if user is None:
            self.commandSock.send(b"430 Invalid username or password.")
            logging.info(f"Invalid username by client {self.clientAddress}")
            return

        self.user.username, self.user.password = user['user'], user['password']
        self.commandSock.send(b"331 User name okay, need password.")

    def PASS(self, args):
        if self.user.username is None:
            self.commandSock.send(b"503 Bad sequence of commands.")
            return

        elif args[0] != self.user.password:
            self.commandSock.send(b"430 Invalid username or password.")
            logging.info(f"Invalid password by client {self.clientAddress}")
            return

        self.commandSock.send(b"230 User logged in, proceed.")
        logging.info(f"Client {self.clientAddress} logged in successfully")
        self.user.loggedIn = True
        self.user.rootDirectory = os.getcwd()
        self.user.WD = self.user.rootDirectory

    def PWD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        if self.user.WD is None:
            self.user.WD = self.user.rootDirectory
        if not os.path.exists(self.user.WD):
            self.errorHappened(f"Client {self.clientAddress} is in unavailable directory")
            self.user.WD = self.user.rootDirectorys
            return
        self.commandSock.send(f"257 {self.user.WD}".encode())
        logging.info(f"Client {self.clientAddress} get his PWD:{self.user.WD}")

    def MKD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        if len(args) == 1:
            try:
                path = os.path.join(self.user.WD, args[0])
                os.mkdir(path)
                self.commandSock.send(b"257 <filename/directory path> created.")
                logging.info(f"Client {self.clientAddress} create new directory:{args[0]}")
            except FileExistsError or OSError:
                self.errorHappened(f"Client {self.clientAddress} create existing dir")
        else:
            try:
                path = os.path.join(self.user.WD, args[1])
                f = open(path, "x");
                f.close()
                self.commandSock.send(b"257 <filename/directory path> created.")
                logging.info(f"Client {self.clientAddress} create new file:{args[1]}")
            except FileExistsError or OSError:
                self.errorHappened(f"Client {self.clientAddress} want to create existing file")

    def RMD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        if len(args) == 1:
            try:
                path = os.path.join(self.user.WD, args[0])
                shutil.rmtree(path)
                self.commandSock.send(b"250 <filename/directory path> deleted.")
                logging.info(f"Client {self.clientAddress} delete directory {args[0]}")
            except OSError:
                self.errorHappened(f"Client {self.clientAddress} want to delete unavailable dir")
        else:
            try:
                path = os.path.join(self.user.WD, args[1])
                os.remove(path)
                self.commandSock.send(b"250 <filename/directory path> deleted.")
                logging.info(f"Client {self.clientAddress} delete file {args[1]}")
            except OSError:
                self.errorHappened(f"Client {self.clientAddress} want to delete unavailable file")

    def LIST(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        try:
            basePath = Path(self.user.WD)
            filesInDir = (file.name for file in basePath.iterdir() if file.is_file())
        except:
            self.errorHappened(f"Can't get files of directory {self.user.WD}")
            return
        client, clientAddr = self.dataSock.accept()
        for file in filesInDir:
            client.send(file.encode())
        client.close()
        self.commandSock.send(b"226 List transfer done.")
        logging.info(f"Client {self.clientAddress} get files of directory {self.user.WD}")

    def CWD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return

        if len(args) == 0:
            self.user.WD = self.user.rootDirectory
            self.commandSock.send(b"250 Successful Change.")
            logging.info(f"Client {self.clientAddress} change his directory to root")

        elif args[0] == '..':
            if self.user.WD == self.user.rootDirectory:
                self.errorHappened(f"Client {self.clientAddress} is in root. Can't do 'cd ..'")
                return
            self.user.WD = Path(self.user.WD).parent
            self.commandSock.send(b"250 Successful Change.")
            logging.info(f"Client {self.clientAddress} change his directory to parent directory")

        elif os.path.exists(os.path.join(self.user.WD, args[0])):
            self.user.WD = os.path.join(self.user.WD, args[0])
            self.commandSock.send(b"250 Successful Change.")
            logging.info(f"Client {self.clientAddress} change his directory to {self.user.WD}")
        else:
            self.errorHappened(f"Client {self.clientAddress} cd to unavailable directory")
            return

    def DL(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        try:
            with open(os.path.join(self.user.WD, args[0]), 'r') as f:
                content = f.read()
                client, clientAddr = self.dataSock.accept()
                client.send(len(content).encode())
                time.sleep(0.5)
                client.sendall(content.encode())
                client.close()
                self.commandSock.send(b"226 Successful Download.")
        except IOError:
            self.errorHappened(f"Client {self.clientAddress} download unavailable file")
            return
        except socket.error as e:
            print(e)

    def sendFile(self, fileContent):
        pass

    def QUIT(self):
        self.commandSock.send(b"221 Successful Quit.")
        self.stop()

    def stop(self):
        self.serverUp = False

    def close(self):
        print('Closing clientSocket')
        self.commandSock.close()
