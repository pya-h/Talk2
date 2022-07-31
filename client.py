import socket
from config import *
import threading
import tkinter as tk
from tkinter import simpledialog, filedialog
import os


class SocketClient:
    def __init__(self, host = SOCKET_HOST, port = SOCKET_PORT):
        self.host = host
        self.port = port
        self.connected = False
        self.chat_mode = False
        self.username = None
        self.ui_initialized = False
        self.socket = None
        self.contact = None
        self.chats = {GROUP: []}

    def ask_client(self, title, message):
        message_box = tk.Tk()
        message_box.withdraw()
        return simpledialog.askstring(title, message, parent=message_box)
 
    def show(self):
        self.ui_initialized = False
        app_thread = threading.Thread(target=self.create_app)
        app_thread.start()

    def create_app(self):
        self.app_window = tk.Tk()
        self.app_window.configure(bg="lightgray")
        self.app_window.minsize(800,600)
        self.app_window.title(APPNAME)

        self.lst_chat_log = tk.Listbox(self.app_window, height=30, width=100)
        self.lst_chat_log.grid(row=0, column=0, sticky='nwse', padx=(10,10), pady=(20,5))
 
        self.lst_clients = tk.Listbox(self.app_window, width=50)
        self.lst_clients.grid(row=0, column=1, columnspan=2, sticky='nwse', padx=(10,10), pady=(20,5))
        self.lst_clients.bind("<<ListboxSelect>>", self.change_contact)
        self.txt_message = tk.Text(self.app_window, height=2)
        self.txt_message.grid(row=1, column=0, sticky='nwse', padx=(10,10), pady=(5,20))
        self.list_scrollbar = tk.Scrollbar(self.app_window)
        self.lst_clients.config(yscrollcommand=self.list_scrollbar.set)
        self.list_scrollbar.config(command=self.lst_clients.yview)

        self.btn_submit = tk.Button(self.app_window, text="Connect", command=self.submit)
        self.btn_submit.grid(row=1,column=1, sticky='nwse', padx=(10,10), pady=(5,20))
        self.btn_submit.config(font=("Calibari", 12), width=10)

        self.btn_send_file = tk.Button(self.app_window, text="File", command=self.send_file)
        self.btn_send_file.grid(row=1,column=2, sticky='nwse', padx=(10,10), pady=(5,20))
        self.btn_send_file.config(font=("Calibari", 12), width=10)
        
        self.app_window.protocol("WM_DELETE_WINDOW", self.close)
        self.ui_initialized = True
        self.app_window.grid_rowconfigure(0, weight=1)
        self.app_window.grid_columnconfigure(0, weight=1)
        self.app_window.mainloop()
    
    def update_clients_list(self, clients):
        self.lst_clients.delete(0, tk.END)
        for client in clients:
            self.lst_clients.insert(tk.END, client if client != self.username else YOU)
        
    def line_separator(self):
        width = self.lst_chat_log.winfo_width()
        line = ''
        for _ in range(width):
            line += '-'
        return line

    def change_contact(self, event):
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            selected_contact = event.widget.get(index)
            self.contact = selected_contact if selected_contact != YOU else self.username
            print(self.chats)
            self.load_current_contacts_chat()
        # else:
        #     self.contact = None

    def break_line(self, lines, pos, chunk_length):
        n = len(lines[pos])
        chunks = [lines[pos][i : i+chunk_length] for i in range(0, n, chunk_length)]
        del lines[pos]
        for i in range(len(chunks)):
            lines.insert(pos + i, chunks[i])
        return lines  # lines is passed by reference and no need to assign lines value again
        # this is for the purposes of chain dots (chain function calls)

    def wrap_text(self, text):
        line_max_length = int(self.lst_chat_log.winfo_width() / 10)
        lines = text.split('\n')
        n = len(lines)
        for i in range(n):
            if i > len(lines): # in case some thing went wrong
                break
            if lines[i] == '' or lines[i] == ' ' or lines[i] == None:
                del lines[i]
                i -= 1
            elif len(lines[i]) > line_max_length:
                lines = self.break_line(lines, i, line_max_length)
        return lines

    def update_chat_log(self, msg, sender):
        if self.ui_initialized:
            lines = self.wrap_text(msg)
            if len(lines) != 0:
                self.lst_chat_log.insert(tk.END, f'{sender}: {lines[0]}' if sender else lines[0])
                del lines[0]
                if lines:
                    for line in lines:
                        self.lst_chat_log.insert(tk.END, f'    {line}')

            self.lst_chat_log.insert(tk.END, self.line_separator())

    def update_chats(self, new_message, partner, sender=None):
        sender = sender if sender else partner
        partner = partner if partner != self.username else YOU
        if partner != SERVER:
            if not partner in self.chats:
                self.chats[partner] = []
            self.chats[partner].append({FROM: sender, MESSAGE: new_message})

    def load_current_contacts_chat(self):
        contact = self.contact if self.contact != self.username else YOU
        self.lst_chat_log.delete(0, tk.END)
        if contact in self.chats:
            for chat in self.chats[contact]:
                self.update_chat_log(chat[MESSAGE], chat[FROM])

    def submit(self):
        if not self.connected:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connected = True
            self.socket.connect((self.host, self.port))
            self.communicate()
            
        if self.chat_mode and self.contact:
            message = self.txt_message.get("1.0", "end")
            self.socket.send(Packet(CHAT, {TARGET_NAME: self.contact, MESSAGE: message}))
            self.txt_message.delete('1.0', tk.END)
            if self.contact != GROUP:
                self.update_chats(message, self.contact, sender=YOU)
                self.update_chat_log(message, sender=YOU)

    def communicate(self):
        thread_receive = threading.Thread(target=self.receive)
        thread_receive.start()
    
    def send_file(self):
        # check file exists?
        if self.socket and self.chat_mode:
            if self.contact:
                filename = filedialog.askopenfilename()
                if filename:
                    filesize = os.path.getsize(filename)
                        # inform server from the file 
                    self.socket.send(Packet(FILE, {DETAILS: f"{filename}{SEPARATOR}{filesize}", TARGET_NAME: self.contact}))
                    # now we send the file
                    progress = Progress(filename=filename, filesize=filesize)
                    with open(filename, "rb") as file:
                        bytes_read = file.read(BUFFER_SIZE)
                        while bytes_read:
                            self.socket.sendall(bytes_read)
                            progress.update(len(bytes_read))
                            bytes_read = file.read(BUFFER_SIZE)
                    self.update_chats(f"FILE: {os.path.basename(filename)} ({FormatFileSize(filesize)})", self.contact)
                    self.update_chat_log(f"FILE: {os.path.basename(filename)} ({FormatFileSize(filesize)})", self.contact)

                else:
                    self.update_chat_log("Please select a valid file", SERVER)
            else:
                self.update_chat_log("Please select a contact first!", SERVER)
        else:
            self.update_chat_log(f"Connection Error", SERVER)

    def close(self):
        self.connected = False
        # send leave response to the server
        if self.socket :
            self.socket.send(Packet(LEAVE, None))
            self.socket.close()
        if self.app_window:
            self.app_window.destroy()
        exit(0)

    def receive(self):
        try:
            while self.connected:
                response = json.loads(self.socket.recv(BUFFER_SIZE))
                if response[TYPE] == INTRODUCE:
                    self.id = response[ATTACHMENTS]
                    while not self.username:
                        self.username = self.ask_client(title="Username", message=f'hey {self.id}\n Server wants to know your username:')
                    self.socket.send(Packet(INTRODUCE, self.username))
                elif response[TYPE] == USERNAME_EXISTS:
                    self.username = None
                    self.id = response[ATTACHMENTS]
                    while not self.username:
                        self.username = self.ask_client("Username", 'username already exists, enter another: ')
                    self.socket.send(Packet(INTRODUCE, self.username))
                elif response[TYPE] == WELCOME:
                    self.update_chat_log(response[ATTACHMENTS], SERVER)
                    self.chat_mode = True
                    self.btn_submit.config(text="Send")
                    self.app_window.title(f"{APPNAME} ({self.username})")
                elif response[TYPE] == CHAT:
                    chat = response[ATTACHMENTS]
                    if not chat[GROUP]:
                        self.update_chats(chat[MESSAGE], chat[FROM])
                    else:
                        self.update_chats(chat[MESSAGE], GROUP, chat[FROM])
                    if chat[FROM] == self.contact or (self.contact == GROUP and chat[GROUP]):
                        self.update_chat_log(chat[MESSAGE], chat[FROM] if chat[FROM] != self.username else YOU)
                elif response[TYPE] == INFORM_CLIENTS:
                    self.update_clients_list(response[ATTACHMENTS])
                elif response[TYPE] == FILE:
                    self.receive_file(response[ATTACHMENTS])

        except ConnectionAbortedError as e:
            if self.socket :
                self.socket.send(Packet(LEAVE))
                self.socket.close()
            self.connected = False
            self.update_chat_log(f"Server connection is lost because: {str(e)}", SERVER)
        except Exception as e:
            if self.socket :
                self.socket.send(Packet(LEAVE))
                self.socket.close()
            self.connected = False
            self.update_chat_log(f"Unknown error occured: {str(e)}", SERVER)

    def receive_file(self, file_details):
        sender = file_details[FROM]
        size = file_details[FILESIZE]
        name = file_details[FILENAME]
        in_group = file_details[GROUP]
        progress = Progress(name, size)
        if not os.path.isdir(DOWNLOADS):
            os.mkdir(DOWNLOADS)
        file_route = f"{DOWNLOADS}/{name}"
        with open(file_route, "wb") as file:
            bytes_received = 0
            while bytes_received < size:
                bytes_read = self.socket.recv(BUFFER_SIZE)
                if not bytes_read:
                    break
                packet_size = len(bytes_read)
                bytes_received += packet_size
                file.write(bytes_read)
                progress.update(packet_size)
        message = f"FILE: {name} ({FormatFileSize(size)})"
        if not in_group:
            self.update_chats(message, sender)
        else:
            self.update_chats(message, GROUP, sender)
        if sender == self.contact or (self.contact == GROUP and in_group):
            self.update_chat_log(message, sender if sender != self.username else YOU)
            
if __name__ == '__main__':
    client = SocketClient()
    client.show()
