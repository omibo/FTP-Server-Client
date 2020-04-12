from constants import *
from user import User
from utils import util

from threading import Thread
from pathlib import Path
import pickle
import socket
import shutil
import os
import logging


class ConnectionThread(Thread):
    def __init__(self, clientSock, clientAddress, dataSock, configs):
        Thread.__init__(self)

        self.commandSock = clientSock
        self.clientAddress = clientAddress
        self.dataSock = dataSock

        self.serverUp = True
        self.user = User()

        self.configs = configs

        self.enableAccounting = None
        self.dataThreshold = None

        self.enableAuth = None

    def setUserAccounting(self):
        accountingConfig = self.configs['accounting']
        self.enableAccounting = accountingConfig['enable']
        self.dataThreshold = int(accountingConfig['threshold'])
        for userDict in accountingConfig['users']:
            if userDict['user'] == self.user.username:
                self.user.setAccounting(userDict)

    def setUserAdministration(self):
        authConfig = self.configs['authorization']
        self.enableAuth = authConfig['enable']
        for user in authConfig['admins']:
            if user == self.user.username:
                self.user.isAdmin = True
                return
        self.user.isAdmin = False
        self.user.adminFiles = authConfig['files']

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
                    continue
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
        self.setUserAccounting()
        self.setUserAdministration()

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
                if not self.handleUserAuth(args[1]):
                    self.commandSock.send(b"550 File unavailable.")
                    logging.info(f"Client {self.clientAddress} does not have access to delete the file {args[0]}")
                    return

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
        self.commandSock.send(CLIENT_READY_TO_RECEIVE_LIST.encode())
        basePath = Path(self.user.WD)
        filesInDir = [file.name for file in basePath.iterdir() if file.is_file()]
        client, clientAddr = self.dataSock.accept()
        sendingStr = pickle.dumps(filesInDir)
        client.sendall(sendingStr)
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

    def handleUserAccounting(self, fileSize):
        if self.enableAccounting:
            if fileSize > self.user.size:
                return False
            self.user.size -= fileSize
            if self.user.size < self.dataThreshold:
                self.sendEmail()
        return True

    def handleUserAuth(self, fileName):
        fileName = './' + fileName
        if self.enableAuth:
            if self.user.isAdmin:
                return True
            if self.user.WD != self.user.rootDirectory:
                return True
            if fileName in self.user.adminFiles:
                return False
        return True

    def DL(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        try:
            with open(os.path.join(self.user.WD, args[0]), 'r') as f:
                content = f.read()
                fileSize = len(content)
                if not self.handleUserAccounting(fileSize):
                    self.commandSock.send(b"425 Can't open data connection.")
                    logging.info(f"Client {self.clientAddress} does not have enough size for download file {args[0]}")
                    return
                if not self.handleUserAuth(args[0]):
                    self.commandSock.send(b"550 File unavailable.")
                    logging.info(f"Client {self.clientAddress} does not have access to download the file {args[0]}")
                    return
                self.commandSock.send(str(fileSize).encode())
                if self.commandSock.recv(RECV_LENGTH).decode() != CLIENT_AGREE_TO_DOWNLOAD_MSG:
                    self.errorHappened(f"Client {self.clientAddress} don't want tp download file")
                    return
                client, clientAddr = self.dataSock.accept()
                client.sendall(content.encode())
                client.close()

                if self.commandSock.recv(RECV_LENGTH).decode() == CLIENT_DOWNLOAD_SUCCESSFULLY:
                    self.commandSock.send(b"226 Successful Download.")
                    logging.info(f"file {args[0]} sent to client {clientAddr} successfully.")
                    return
                else:
                    logging.info(f"file {args[0]} sent to client {clientAddr} unsuccessfully.")

        except IOError:
            self.errorHappened(f"Client {self.clientAddress} download unavailable file")
            return
        except socket.error as e:
            print(e)

    def QUIT(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        self.commandSock.send(b"221 Successful Quit.")
        logging.info(f"Client {self.clientAddress} logged out")
        self.stop()

    def HELP(self, args):
        self.commandSock.send(b"214\n salammmmmmmmmmmmmmm")
        logging.info(f"Client {self.clientAddress} get help of server")

    def stop(self):
        self.serverUp = False

    def close(self):
        logging.info(f"Connection by {self.clientAddress} closed")
        self.commandSock.close()
