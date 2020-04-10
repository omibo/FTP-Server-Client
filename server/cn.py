from socket import *
import base64

def toByteArray(s):
  return bytes(s, 'utf-8')

def sendMail(mailserver, domain, toEmailAddress, username, password):
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
  print(recv)
  try:
    for msg in messages:
      clientSocket.send(msg)
      recv = clientSocket.recv(1024)
      print(recv)
  except Exception as e:
    print(e)
  clientSocket.close()

#usage:
mailserver = ("mail.ut.ac.ir", 587)
sendMail(mailserver, "ut.ac.ir", "shbmobina@gmail.com", "omid", "omid")