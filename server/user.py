
class User:
    def __init__(self):
        self.username = None
        self.password = None
        self.loggedIn = False

        self.WD = None
        self.rootDirectory = None

        self.size = None
        self.email = None
        self.alert = None

    def setAccounting(self, user):
        self.size = user['size']
        self.email = user['email']
        self.alert = user['alert']

