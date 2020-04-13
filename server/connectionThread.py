from globals.constants import *
from server.user import User
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
        logging.warning(f"Client {self.clientAddress} proceeded to do PWD without login")

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
                logging.info(f"Command '{commandMsg}' received from client {self.clientAddress}")
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
            logging.info(f"Invalid username entered by client {self.clientAddress}")
            return

        self.user.username, self.user.password = user['user'], user['password']
        self.commandSock.send(b"331 User name okay, need password.")

    def PASS(self, args):
        if self.user.username is None:
            self.commandSock.send(b"503 Bad sequence of commands.")
            return

        elif args[0] != self.user.password:
            self.commandSock.send(b"430 Invalid username or password.")
            logging.info(f"Invalid password enetered by client {self.clientAddress}")
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
            self.errorHappened(f"Client {self.clientAddress} is in an unavailable directory")
            self.user.WD = self.user.rootDirectory
            return
        self.commandSock.send(f"257 {self.user.WD}".encode())
        logging.info(f"Client {self.clientAddress} got PWD:{self.user.WD}")

    def MKD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        if len(args) == 1:
            try:
                path = os.path.join(self.user.WD, args[0])
                os.mkdir(path)
                self.commandSock.send(b"257 " + args[0].encode() + b" created.")
                logging.info(f"Client {self.clientAddress} created new directory:{args[0]}")
            except FileExistsError or OSError:
                self.errorHappened(f"Client {self.clientAddress} proceeds to create an existing dir")
        else:
            try:
                path = os.path.join(self.user.WD, args[1])
                f = open(path, "x");
                f.close()
                self.commandSock.send(b"257 " + args[1].encode() + b" created.")
                logging.info(f"Client {self.clientAddress} created new file:{args[1]}")
            except FileExistsError or OSError:
                self.errorHappened(f"Client {self.clientAddress} proceeds to create an existing file")

    def RMD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return
        if len(args) == 2:
            try:
                path = os.path.join(self.user.WD, args[1])
                shutil.rmtree(path)
                self.commandSock.send(b"250 " + args[1].encode() + b" deleted.")
                logging.info(f"Client {self.clientAddress} deleted directory {args[1]}")
            except OSError:
                self.errorHappened(f"Client {self.clientAddress} proceeds to delete unavailable dir")
        else:
            try:
                if not self.handleUserAuth(args[0]):
                    self.commandSock.send(b"550 File unavailable.")
                    logging.info(f"Client {self.clientAddress} does not have access to delete file {args[0]}")
                    return

                path = os.path.join(self.user.WD, args[1])
                os.remove(path)
                self.commandSock.send(b"250 " + args[0].encode() + b" deleted.")
                logging.info(f"Client {self.clientAddress} deleted file {args[0]}")
            except OSError:
                self.errorHappened(f"Client {self.clientAddress} proceeds to delete an unavailable file")

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
        logging.info(f"Client {self.clientAddress} got list of directory {self.user.WD}")

    def CWD(self, args):
        if not self.user.loggedIn:
            self.userNotLoggedIn()
            return

        if len(args) == 0:
            self.user.WD = self.user.rootDirectory
            self.commandSock.send(b"250 Successful Change.")
            logging.info(f"Client {self.clientAddress} changed the directory to root")

        elif args[0] == '..':
            if self.user.WD == self.user.rootDirectory:
                self.errorHappened(f"Client {self.clientAddress} is in root. Can not proceed 'cd ..'")
                return
            self.user.WD = Path(self.user.WD).parent
            self.commandSock.send(b"250 Successful Change.")
            logging.info(f"Client {self.clientAddress} changed the directory to the parent directory")

        elif os.path.exists(os.path.join(self.user.WD, args[0])):
            self.user.WD = os.path.join(self.user.WD, args[0])
            self.commandSock.send(b"250 Successful Change.")
            logging.info(f"Client {self.clientAddress} changed the directory to {self.user.WD}")
        else:
            self.errorHappened(f"Client {self.clientAddress} changed the directory to an unavailable path")
            return

    def handleUserAccounting(self, fileSize):
        if self.enableAccounting:
            if fileSize > self.user.size:
                return False
            self.user.size -= fileSize
            if self.user.size < self.dataThreshold:
                self.sendEmail(self.user.email)
        return True

    def sendEmail(self, userEmail):
        mailserver = ("mail.ut.ac.ir", 587)
        util.sendEmailUtil(mailserver, "ut.ac.ir", userEmail, "omid", "1234")

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
                if not self.handleUserAuth(args[0]):
                    self.commandSock.send(b"550 File unavailable.")
                    logging.info(f"Client {self.clientAddress} does not have access to download the file {args[0]}")
                    return
                if not self.handleUserAccounting(fileSize):
                    self.commandSock.send(b"425 Can't open data connection.")
                    logging.info(f"Client {self.clientAddress} does not have enough available size to download the file {args[0]}")
                    return
                self.commandSock.send(str(fileSize).encode())
                if self.commandSock.recv(RECV_LENGTH).decode() != CLIENT_AGREE_TO_DOWNLOAD_MSG:
                    self.errorHappened(f"Client {self.clientAddress} does not agree to download file")
                    return
                client, clientAddr = self.dataSock.accept()
                client.sendall(content.encode())
                client.close()

                if self.commandSock.recv(RECV_LENGTH).decode() == CLIENT_DOWNLOAD_SUCCESSFULLY:
                    self.commandSock.send(b"226 Successful Download.")
                    logging.info(f"file {args[0]} has been successfully sent to client {clientAddr}")
                    return
                else:
                    logging.info(f"file {args[0]} has not been sent to client {clientAddr}")

        except IOError:
            self.errorHappened(f"Client {self.clientAddress} proceeds to download an unavailable file.")
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
        self.commandSock.send(b"214\nUSER [name], Its argument is used to specify the user's name. It is used for user authentication.\nPASS [password], Its argument is used to specify the user's password. It is used for user authentication.\nPWD, It is used to print out the current working directory.\nMKD [flag] [path], Its first argument represents the type, '-i' for a new file and none for a new directory. Its second argument is used to specify the path and name of the file/directory. It is used to create a new file or directory.\nRMD [flag] [path], Its first argument represents the type, '-f' for a directory and none for a file. Its second argument is used to specify the path and name of the file/directory. It is used to remove a file or directory.\nLIST, It is used to print out the list of files/directories in current working directory.\nCWD [path], Its argument is used to specify the path. It is used to change the current working directory to a desired path.\nDL [name], Its argument is used to specify the file's name. It is used to download a file.\nHELP, It is used to print out the list of available commands and their details.\nQUIT, It is used to log out from the server.\n")
        logging.info(f"Client {self.clientAddress} got the help message from the server")

    def stop(self):
        self.serverUp = False

    def close(self):
        logging.info(f"Connection by {self.clientAddress} got closed")
        self.commandSock.close()
