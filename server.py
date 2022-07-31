import socket
import time
from uuid import uuid4
from config import *
import threading
import os

class Client:
    def __init__(self, socket, id, ip, connection_date, username = None):
        self.socket = socket
        self.id = id
        self.ip = ip
        self.connection_date = connection_date
        self.username = username


class SocketServer:

    def __init__(self, host = SOCKET_HOST, port = SOCKET_PORT):
        self.clients = {}
        self.rooms = {GROUP: {}}
        self.port = port
        self.host = host
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))

    def start(self):
        self.server.listen()
        print(f'server started listening on {self.host}:{self.port}')
        while True:
            client_socket, ip_address = self.server.accept()
            uid = uuid4()
            client_id = str(uid)
            self.clients[client_id] = Client(socket=client_socket, id=uid, ip=ip_address, connection_date=time.ctime())
            client = self.clients[client_id]
            packet = Packet(INTRODUCE, client_id)
            client.socket.send(packet)
            # receive the client's username
            thread = threading.Thread(target=self.listen, args=(client_id,))
            thread.start()
            # client.socket.close()

    def list_clients(self):
        client_usernames = [GROUP]
        for cid in self.clients:
            if self.clients[cid].username:
                client_usernames.append(self.clients[cid].username)
        return client_usernames

    def listen(self, client_id):
        client = self.clients[client_id]
        try:
            while True: 
                packet = client.socket.recv(BUFFER_SIZE)
                if(packet):
                    response = json.loads(packet)
                    if response[TYPE] == INTRODUCE:
                        username = response[ATTACHMENTS]
                        if not self.find_client(username=username) and username != GROUP and username != YOU:
                            client.username = username
                            client.socket.send(Packet(WELCOME, f"Hi {client.username} \n"))
                            index = len(self.clients)
                            print('client#%d: %s(%s), from: %s, on: %s' 
                                % (index, str(client.username), client_id, str(client.ip), str(client.connection_date)))
                            # inform others that new client has came online
                            self.broadcast(Packet(INFORM_CLIENTS, self.list_clients()))
                        else:
                            client.socket.send(Packet(USERNAME_EXISTS))
                    elif response[TYPE] == CHAT:
                        chat = response[ATTACHMENTS]
                        if chat[TARGET_NAME] != GROUP:
                            self.send_message(sender_name=client.username, target_name=chat[TARGET_NAME], message=chat[MESSAGE])
                        else:
                            self.broadcast(Packet(CHAT, {FROM: client.username, MESSAGE: chat[MESSAGE], GROUP: True}))
                    elif response[TYPE] == FILE:
                        target_name = response[ATTACHMENTS][TARGET_NAME]
                        if target_name != GROUP:
                            self.pass_file(client, target_name, response[ATTACHMENTS][DETAILS])
                        else:
                            self.broadcast_file(client, response[ATTACHMENTS][DETAILS])
                    elif response[TYPE] == LEAVE:
                        self.disconnect_client(client_id)
                        break
                else:
                    client.socket.close()
        except Exception as e:
            print(str(e))
            self.disconnect_client(client_id)

    def disconnect_client(self, client_id):
        print(f"{self.clients[client_id].username} has been disconnected!")
        self.clients[client_id].socket.close()
        del self.clients[client_id]
        self.broadcast(Packet(INFORM_CLIENTS, self.list_clients()))

    def broadcast(self, packet):
        # send message for all users
        for cid in self.clients:
            self.clients[cid].socket.send(packet)

    def broadcast_file(self, client, file_details):
        # send message for all users
        sender_id = str(client.id)
        filename, filesize = file_details.split(SEPARATOR)
        filename = os.path.basename(filename)
        filesize = int(filesize)
        progress = Progress(filename, filesize)
        bytes_sent = 0
        file_bytes = []
        while bytes_sent < filesize:
            bytes_read = client.socket.recv(BUFFER_SIZE)
            if not bytes_read:
                break
            file_bytes.append(bytes_read)
            packet_size = len(bytes_read)
            bytes_sent += packet_size
            progress.update(packet_size)
        
        for cid in self.clients:
            if cid != sender_id:
                self.clients[cid].socket.send(Packet(FILE, {FROM: client.username, FILESIZE: filesize, FILENAME: filename, GROUP: True}))
                for byte in file_bytes:
                    self.clients[cid].socket.sendall(byte)
                    progress.update(len(byte))

    def find_client(self, username=None, id=None):
        if username:
            for user_id in self.clients:
                if self.clients[user_id].username == username:
                    return user_id
        elif id:
            id if id in self.clients else None
        return None

    def send_message(self, sender_name, target_name, message):
        target_id = self.find_client(username=target_name)
        if target_id:
            packet = Packet(CHAT, {FROM: sender_name, MESSAGE: message, GROUP: False})
            self.clients[target_id].socket.send(packet)
            print(packet)
            return True
        return False

    def pass_file(self, client, target_name, file_details):
        filename, filesize = file_details.split(SEPARATOR)
        filename = os.path.basename(filename)
        filesize = int(filesize)
        target_id = self.find_client(username=target_name)
        self.clients[target_id].socket.send(Packet(FILE, {FROM: client.username, FILESIZE: filesize, FILENAME: filename, GROUP: False}))
        if target_id:
            progress = Progress(filename, filesize)
            bytes_sent = 0
            while bytes_sent < filesize:
                bytes_read = client.socket.recv(BUFFER_SIZE)
                if not bytes_read:
                    break
                self.clients[target_id].socket.sendall(bytes_read)
                packet_size = len(bytes_read)
                bytes_sent += packet_size
                progress.update(packet_size)

            print(f"file: {filename} passed successfully to {target_name}")
if __name__ == '__main__':
    socket_server = SocketServer()
    socket_server.start()