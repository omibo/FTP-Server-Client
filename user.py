
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

        self.isAdmin = False
        self.adminFiles = None

    def setAccounting(self, user):
        self.size = int(user['size'])
        self.email = user['email']
        self.alert = user['alert']

