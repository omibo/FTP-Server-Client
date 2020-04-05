import json


def getConfigs():
    with open("../config.json") as configFile:
        return json.load(configFile)
