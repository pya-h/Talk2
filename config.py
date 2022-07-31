import json
import tqdm

(APPNAME, ) = ("ChatApp", )
KEYS_SOCKET = (SOCKET_HOST, SOCKET_PORT,) = ('localhost', 6660, )

KEYS_RESPONSE = (TYPE, ATTACHMENTS, INTRODUCE, WELCOME, USERNAME_EXISTS, INFORM_CLIENTS, CHAT, FILE, LEAVE) \
    = ('type', 'attachments', 'introduce', 'welcome', 'username_exists', 'inform_clients', 'chat', 'file', 'leave')

KEYS_CHAT = (TARGET_NAME, MESSAGE, FROM, GROUP, YOU, SERVER) = ('target_username', 'message', 'from', '(Group)', 'You', 'Server')
KEYS_FILE = (SEPARATOR, BUFFER_SIZE, DETAILS, FILESIZE, FILENAME, DOWNLOADS) = ('<<->>', 1024, 'details', 'filesize', 'filename', 'downloads')
def Packet(res_type, atachments = None):
    pack = {TYPE: res_type, ATTACHMENTS: atachments}
    return json.dumps(pack).encode('utf-8')

def Progress(filename, filesize):
    return tqdm.tqdm(range(filesize), f"file: {filename}", unit="B", unit_scale=True, unit_divisor=1024)

def Round(num):
    return round(num * 100) / 100

def FormatFileSize(size):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'EB']
    index = 0
    while size >= 1024:
        index += 1
        size /= 1024
    return f"{Round(size)} {units[index]}"
