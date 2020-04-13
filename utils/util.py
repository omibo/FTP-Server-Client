from globals.constants import *
from socket import socket, AF_INET, SOCK_STREAM
import base64
import json


def getConfigs():
    with open("config.json") as configFile:
        return json.load(configFile)


def validateCommand(inputCommand):
    args = SERVER_COMMANDS.get(inputCommand[0])
    if args is None:
        return False
    if type(args) is list:
        if len(inputCommand) not in args:
            return False
        if inputCommand[0] == 'MKD':
            if len(inputCommand) == 3:
                return inputCommand[1] == '-i'
        elif inputCommand[0] == 'RMD':
            if len(inputCommand) == 3:
                return inputCommand[1] == '-f'

        elif inputCommand[0] == 'CWD':
            return True
    else:
        return args == len(inputCommand)
    return True


def findUser(username):
    for user in getConfigs()['users']:
        if user['user'] == username:
            return user
    return None

def toByteArray(s):
  return bytes(s, 'utf-8')

def sendEmailUtil(mailserver, domain, toEmailAddress, username, password):
  fromEmailAddress = username + "@" + domain
  base64Username = base64.b64encode(toByteArray(username + "\r\n")).decode("ascii")
  base64Password = base64.b64encode(toByteArray(password)).decode("ascii")
  username = toByteArray(base64Username + "\r\n")
  password = toByteArray(base64Password + "\r\n")
  messages = [toByteArray("HELO " + fromEmailAddress + "\r\n"),
    b"AUTH LOGIN\r\n", username, password,
    toByteArray("MAIL from:<" + fromEmailAddress + ">\r\n"),
    toByteArray("RCPT to:<" + toEmailAddress + ">\r\n"),
    b"DATA\r\n",
    toByteArray("from: UT CN FTP Server <utcnftpserver@ut.ac.ir>\r\nto: " + toEmailAddress + "\r\nSubject: FTP Server Data Usage Limit Warning\r\nHi,\r\nYour monthly data usage limit has been exceeded.\r\nUT CN FTP Server\r\n.\r\n"),
    b"quit\r\n"]
  clientSocket = socket(AF_INET, SOCK_STREAM)
  clientSocket.connect(mailserver)
  recv = clientSocket.recv(1024)
  try:
    for msg in messages:
      clientSocket.send(msg)
      recv = clientSocket.recv(1024)
  except Exception as e:
    print(e)
  clientSocket.close()
