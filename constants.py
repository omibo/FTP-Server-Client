SERVER_IP_ADDRESS = '0.0.0.0'
MAX_CLIENT_IN_QUEUE = 5
RECV_LENGTH = 1024
SEND_LENGTH = 1024

SERVER_COMMANDS = {'USER': 2, 'PASS': 2, 'PWD': 1, 'MKD': [2, 3], 'RMD': [2, 3],
                   'LIST': 1, 'CWD': [1, 2], 'DL': 2, "HELP": 1, 'QUIT': 1}
