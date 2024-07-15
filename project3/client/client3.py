"""
Project 3
Client
"""
import socket
import struct
import pickle
import select
import os
import tkinter as tk
from tkinter.filedialog import askopenfilename
import threading
from queue import Queue
import time


class Command:
    """
    Used for socket transmission
    """
    command = ""
    payload = ""


class Application:
    """
    https://github.com/chenstarx/socket-demo-with-GUI
    https://www.tutorialspoint.com/python/tk_button.htm
    """
    def __init__(self, host, port1, port2):
        self.host = host  # host address
        self.port1 = port1  # primary port number
        self.port2 = port2  # backup port
        self.event = threading.Event()
        self.root = tk.Tk()  # use tk as gui
        self.root.title("File transfer")  # tk gui's title
        self.frm = tk.Frame(self.root)  # tk frame
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # client socket
        self.username = None  # client username
        self.lexicon_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # lexicon socket
        self.q = Queue()  # user input queue
        self.primary_connected = True

        # Mid
        self.frm_M = tk.Frame(self.frm)  # middle frame
        self.scrollbar = tk.Scrollbar(master=self.frm_M)  # scrollbar for listbox
        self.listbox = tk.Listbox(  # listbox for display
            master=self.frm_M,
            yscrollcommand=self.scrollbar.set
        )
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=False)  # pack gui components
        self.listbox.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.username_entry = tk.Entry(master=self.frm_M)
        self.username_entry.pack(expand=True)
        self.username_entry.bind("<Return>", lambda x: self.connect(self.username_entry, self.port1))
        # bind text input to connect function
        self.lexicon_entry = tk.Entry(master=self.frm_M)
        self.lexicon_entry.pack(expand=True)
        self.lexicon_entry.bind("<Return>", lambda x: self.add_lexicon(self.lexicon_entry))
        # connect, add lexicon, upload, exit buttons
        tk.Button(self.frm_M, text='Connect', command=lambda: self.connect(self.username_entry, self.port1),
                  width=15).pack(side=tk.TOP)
        tk.Button(self.frm_M, text='Add lexicon', command=lambda: self.add_lexicon(self.lexicon_entry),
                  width=15).pack(side=tk.TOP)
        tk.Button(self.frm_M, text='Upload', command=self.upload, width=15).pack(side=tk.TOP)
        tk.Button(self.frm_M, text='Exit', command=self.exit, width=15).pack(side=tk.TOP)
        self.frm_M.pack(side=tk.LEFT)

        self.frm.pack()

    def connect(self, text_input, port):  # connect client to server
        self.username = text_input.get()  # get username from user input
        # text_input.delete(0, tk.END)  # clear text input
        self.connect_lexicon(port)
        self.sock.connect((self.host, port))  # connect socket to host address and port
        self.send_connect()

        self.check_primary_th = threading.Thread(target=self.check_primary,)
        self.check_primary_th.start()

    def send_connect(self):
        try:
            add_command = Command()  # command to send
            add_command.command = f'Connect {self.username}'  # set command as connect + username
            add_command.payload = self.username  # set username as payload
            packed_data = pickle.dumps(add_command)  # dumps command to pickle data
            self.sock.sendall(struct.pack('i', len(packed_data)))  # send data length
            self.sock.sendall(packed_data)  # send data

            reply_len = struct.unpack("i", self.sock.recv(4))[0]  # receive msg from server
            data = bytearray()  # received data placeholder
            while reply_len > len(data):  # continue to receive data from server
                data += self.sock.recv(reply_len - len(data))
            reply_command = pickle.loads(data)  # Receive the server reply
            server_command = reply_command.command.split(" ")
            if server_command[0] == "connected":  # when server echoed connected
                username = reply_command.payload  # get reply payload
                self.listbox.delete(0, tk.END)  # clear listbox
                self.listbox.insert(0, f'{username} connected')  # insert username connected
            elif server_command[0] == 'conflict':  # when server echoed username conflict
                username = reply_command.payload  # get username from payload
                self.listbox.delete(0, tk.END)  # clear listbox
                self.listbox.insert(0, f'{username} conflicted')  # insert username conflict

        except Exception as e:  # print exception
            print('Error in connect: ', e)

    def connect_lexicon(self, port):
        """
        connect lexicon socket to server
        """
        self.lexicon_sock.connect((self.host, port))
        self.send_connect_lex()

        self.wait_poll_th = threading.Thread(target=self.wait_poll, )
        self.wait_poll_th.start()

    def send_connect_lex(self):
        try:
            add_command = Command()
            add_command.command = f'Connect {self.username}_lex'
            add_command.payload = self.username + '_lex'
            packed_data = pickle.dumps(add_command)
            self.lexicon_sock.sendall(struct.pack('i', len(packed_data)))
            self.lexicon_sock.sendall(packed_data)

            reply_len = struct.unpack("i", self.lexicon_sock.recv(4))[0]
            data = bytearray()
            while reply_len > len(data):
                data += self.lexicon_sock.recv(reply_len - len(data))
            reply_command = pickle.loads(data)  # Receive the server reply
            server_command = reply_command.command.split(" ")
            print('connect_lex: ', server_command)

        except Exception as e:
            print('Error in connect_lexicon: ', e)

    def check_primary(self):
        """
        check whether primary server socket is open
        has error: debug
        """
        while self.primary_connected:
            if self.sock.fileno() == -1 or self.lexicon_sock.fileno() == -1:
                self.primary_connected = False
                print('check_primary')
                self.sock.close()
                self.lexicon_sock.close()
                self.connect_backup()

    def connect_backup(self):
        """
        reconnect client to backup
        """
        # self.listbox.insert(tk.END, 'Primary not available')

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lexicon_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port2))
        self.lexicon_sock.connect((self.host, self.port2))

        self.send_connect()
        self.send_connect_lex()
        self.listbox.insert(tk.END, 'Primary not available')
        self.listbox.insert(tk.END, 'Connected to backup')
        self.wait_poll()

    def add_lexicon(self, lexicon_entry):
        """
        parse lexicon entry, add to queue
        """
        lexicon = lexicon_entry.get()
        lexicon_entry.delete(0, tk.END)
        self.q.put(lexicon)
        self.listbox.insert(tk.END, f'queue add: {lexicon}')

    def wait_poll(self):
        """
        wait for server send poll command
        """
        try:
            while self.lexicon_sock.fileno() != -1:
                a = self.lexicon_sock.recv(4)
                print("Wanted 4 bytes got " + str(len(a)) + " bytes")

                if len(a) < 4:
                    raise Exception("client closed socket, ending client thread")

                message_length = struct.unpack('i', a)[0]
                print("Message Length: ", message_length)
                data = bytearray()
                while message_length > len(data):
                    data += self.lexicon_sock.recv(message_length - len(data))

                new_command = pickle.loads(data)
                print("\nCommand is: ", new_command.command.replace('_', ' '))
                server_command = new_command.command.split(" ")
                # Divide the command to recognize it, " " is the divider
                reply_command = Command()

                if server_command[0] == "poll":
                    reply_command.command = 'addlexicon'
                    if self.q.empty():
                        reply_command.payload = ''
                    else:
                        reply_command.payload = ' '.join(list(self.q.queue))
                        self.q.queue.clear()

                    # self.listbox.delete(1, tk.END)
                    self.listbox.insert(tk.END, f'polled queue: {reply_command.payload}')

                elif server_command[0] == 'addlexicon':
                    print("server_command[0] == 'addlexicon'")
                    continue
                else:
                    # handle unknown command
                    print("Unknown Command2:", new_command.command.replace('_', ' '))
                    raise Exception("Unknown Command")

                packed_data = pickle.dumps(reply_command)  # Serialize the class to a binary array
                # Length of the message is just the length of the array
                self.lexicon_sock.sendall(struct.pack("i", len(packed_data)))
                self.lexicon_sock.sendall(packed_data)
                print('sent queue')

        except Exception as e:
            print("error in wait_poll: ", e)
            self.lexicon_sock.close()

    def upload(self):  # upload file to server
        """
        https://docs.python.org/3/library/dialog.html
        """
        try:
            filename = askopenfilename()  # prompt a file selection window
            add_command = Command()  # command to send
            add_command.command = f"Upload {filename.replace(' ', '_')}"  # set command
            file = open(filename, 'rb')  # open txt file
            add_command.payload = file.read()  # put file to payload
            file.close()  # close file handler

            packed_data = pickle.dumps(add_command)  # dumps command to pickle data
            self.sock.sendall(struct.pack("i", len(packed_data)))  # send data length
            self.sock.sendall(packed_data)  # send data

            reply_len = struct.unpack("i", self.sock.recv(4))[0]  # get server echoed msg
            data = bytearray()  # server echoed msg placeholder
            while reply_len > len(data):  # continue to receive server msg
                data += self.sock.recv(reply_len - len(data))
            reply_command = pickle.loads(data)  # Receive the server reply

            server_command = reply_command.command.split(" ")  # parse reply command
            if server_command[0] == "Uploaded":  # when server returned uploaded file
                server_filename = server_command[1]  # get server returned filename
                self.listbox.insert(tk.END, "Server echoed file: ", server_filename)  # put this msg into listbox
                server_file = open(server_filename, 'wb')  # open the received file
                server_file.write(reply_command.payload)  # write payload to file content
                server_file.close()  # close file handler
                return server_filename

        except Exception as e:
            print("error in upload: ", e)

    def exit(self):
        try:
            # send exit message
            add_command = Command()  # create a command
            add_command.command = 'exit'  # set exit as command
            add_command.payload = self.username  # set username as payload
            packed_data = pickle.dumps(add_command)  # pickle dumps command
            self.sock.sendall(struct.pack('i', len(packed_data)))  # send data length
            self.sock.sendall(packed_data)  # send data

            reply_len = struct.unpack("i", self.sock.recv(4))[0]  # get server echoed msg
            data = bytearray()  # server echoed msg placeholder
            while reply_len > len(data):  # continue to receive server msg
                data += self.sock.recv(reply_len - len(data))
            reply_command = pickle.loads(data)  # Receive the server reply
            self.listbox.insert(tk.END, "server echoed: ", reply_command.payload)  # update listbox
            # kill itself
            self.sock.close()
            self.lexicon_sock.close()
            os._exit(0)

        except Exception as ex:
            print('error in exit: ', ex)


def main():
    # host address and port #, should be the same as the server
    host = "localhost"
    port1 = 7789
    port2 = 9789

    app = Application(host, port1, port2)  # instantiate a client
    app.root.mainloop()  # client tk gui mainloop
    app.sock.close()  # close the client socket


if __name__ == '__main__':
    main()
