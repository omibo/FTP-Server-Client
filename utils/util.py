from constants import SERVER_COMMANDS

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
