"""
Pr 3
Backup server
"""
import socket
import threading
import struct
import pickle
import select
import os
import tkinter as tk
import time


class Command:
    """
    data struct used between client-server
    """
    command = ""
    payload = ""


class ServerThread(threading.Thread):
    """
    https://github.com/chenstarx/socket-demo-with-GUI
    https://www.tutorialspoint.com/python/tk_button.htm
    """

    def __init__(self, socket_instance, connections, correct_words):
        threading.Thread.__init__(self)  # call base constructor
        self.username = None
        self.my_socket = socket_instance  # server thread
        self.connections = connections  # server connections
        self.correct_words = correct_words  # correct words dictionary

    def run(self):
        try:
            while True:
                print("Reading initial length")
                a = self.my_socket.recv(4)  # receive msg from client
                print("Wanted 4 bytes got " + str(len(a)) + " bytes")

                if len(a) < 4:  # boundary check
                    raise Exception("client closed socket, ending client thread")

                message_length = struct.unpack('i', a)[0]  # unpack received msg
                print("Message Length: ", message_length)
                data = bytearray()  # data placeholder
                while message_length > len(data):  # receive data
                    data += self.my_socket.recv(message_length - len(data))

                new_command = pickle.loads(data)
                print("\nCommand is: ", new_command.command.replace('_', ' '))

                client_command = new_command.command.split(" ")
                # Divide the command to recognize it, " " is the divider
                reply_command = Command()
                if client_command[0] == "Connect":
                    self.username = new_command.payload  # unload the username from payload
                    reply_command = self.username_check()  # do username check
                    if reply_command.command == 'conflict':  # check duplicate username
                        packed_data = pickle.dumps(reply_command)  # Serialize the class to a binary array
                        # Length of the message is just the length of the array
                        self.my_socket.sendall(struct.pack("i", len(packed_data)))  # send data length
                        self.my_socket.sendall(packed_data)  # send data
                        self.my_socket.close()  # close this thread
                        break

                elif client_command[0] == "Upload":  # handles uploaded file
                    filename = client_command[1].split('/')[-1]  # get the received filename
                    server_filename = 'server_received_' + filename
                    file = open(server_filename, 'wb')  # wb means write bytes
                    file.write(new_command.payload)  # write bytes to file
                    file.close()  # close file handler
                    # add lexicon check here
                    self.spell_check(server_filename)  # do spell check

                    reply_command.command = "Uploaded " + server_filename  # edit reply command
                    server_file = open(server_filename, 'rb')  # open modified file
                    reply_command.payload = server_file.read()  # put file to payload
                    server_file.close()  # close file

                elif client_command[0] == 'addlexicon':
                    new_words = new_command.payload.split(' ')  # get queue words
                    print('new_words: ', new_words)
                    for word in new_words:
                        print('word: ', word)
                        if word not in self.correct_words:
                            self.correct_words.append(word)
                    continue

                elif client_command[0] == 'exit':  # handles client exit
                    reply_command.command = 'exit'  # return exit command
                    reply_command.payload = 'done'  # edit exit payload
                    packed_data = pickle.dumps(reply_command)  # Serialize the class to a binary array
                    # Length of the message is just the length of the array
                    self.my_socket.sendall(struct.pack("i", len(packed_data)))  # send data length
                    self.my_socket.sendall(packed_data)  # send data
                    self.my_socket.close()  # close this thread
                    break
                else:
                    # handle unknown command
                    print("Unknown Command:", new_command.command.replace('_', ' '))
                    raise Exception("Unknown Command")

                packed_data = pickle.dumps(reply_command)  # Serialize the class to a binary array
                # Length of the message is just the length of the array
                self.my_socket.sendall(struct.pack("i", len(packed_data)))  # send data length
                self.my_socket.sendall(packed_data)  # send data

        except Exception as e:  # handle above exceptions
            print(e)
            print("\nClosing socket")
            self.my_socket.close()

    def spell_check(self, server_filename):
        """
        http://openbookproject.net/courses/python4fun/spellcheck.html
        :return:
        """
        modified_lines = []  # modified lines placeholder
        f = open(server_filename)  # open received file
        lines = list(f)  # put received file into a list
        f.close()  # close received file
        for i, line in enumerate(lines):  # for each line
            line = line.strip()  # remove the \n
            file_words = line.split()  # split by space
            for j, txt_word in enumerate(file_words):  # for each word in a line
                if txt_word not in self.correct_words:  # if a word is not in the correct_words list
                    file_words[j] = f"[{txt_word}]"  # add brackets
            modified_lines.append(' '.join(file_words) + '\n')  # put modified line back to modified list

        with open(server_filename, 'w') as f:
            f.writelines(modified_lines)  # write back the modified file

    def username_check(self):
        usernames = []  # current username list
        reply_command = Command()  # reply msg
        reply_command.payload = self.username  # set payload as username
        for cli_thread in self.connections:  # for each client thread in connections
            usernames.append(cli_thread.username)  # append existing username to usernames
        if self.username in usernames:  # if new username exists
            reply_command.command = 'conflict'  # set conflict
        else:
            reply_command.command = "connected"  # set connected

        return reply_command


class Server(threading.Thread):
    """
    https://docs.python.org/3/library/tkinter.html
    https://www.tutorialspoint.com/python/tk_label.htm
    https://www.tutorialspoint.com/python/tk_listbox.htm
    """

    def __init__(self, host, port1, port2):
        super(Server, self).__init__()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # instantiate a socket
        self.wait_push_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket waits primary push lexicon
        self.root = tk.Tk()  # tk gui
        self.root.title("Backup server status")  # set server gui title
        self.root.geometry('250x250')  # set server gui size
        self.frm = tk.Frame(self.root, )  # add frame
        self.connections = []  # list holds client connections
        self.host = host  # host ip
        self.port1 = port1  # primary port
        self.port2 = port2  # backup port
        self.correct_words = open("correct.words").readlines()  # open the correct word file
        self.correct_words = [word.strip() for word in self.correct_words]  # put correct words in a list
        self.correct_words = list(set(self.correct_words))  # remove duplicates
        self.primary_connected = True

        # GUI
        self.frm_m = tk.Frame(self.frm, )  # add middle frame
        self.var = tk.StringVar()  # label content variable
        self.label = tk.Label(self.root, textvariable=self.var, relief=tk.RAISED)  # tk label
        self.var.set('Connected usernames')  # set label content
        self.scrollbar = tk.Scrollbar(master=self.frm_m)  # scrollbar to the listbox
        # listbox to display connections
        self.listbox = tk.Listbox(master=self.frm_m, yscrollcommand=self.scrollbar.set, )
        # button to refresh connections
        tk.Button(self.frm_m, text='Refresh', command=self.refresh, width=15).pack(side=tk.BOTTOM)
        # server exit button
        tk.Button(self.frm_m, text='Exit', command=self.exit, width=15).pack(side=tk.BOTTOM)
        # pack components to gui
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        self.listbox.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.label.pack()
        self.frm_m.pack()
        self.frm.pack()

    def run(self):
        """
        https://pymotw.com/2/select/#poll
        """
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # set reuse socket
        self.server_socket.bind((self.host, self.port2))  # bind host address and port
        self.server_socket.listen(1)  # listen for incoming connection
        print(f"Backup listening on {self.port2}")

        self.connect_primary()

        self.lex_th = threading.Thread(target=self.add_lexicon)
        self.lex_th.start()

        while True:
            if self.server_socket.fileno() != -1:
                (client_socket, address) = self.server_socket.accept()  # server socket accepting client connection
                print("Incoming connection ", )
                client_socket.setblocking(True)
                # make a new instance of our thread class to handle requests
                new_thread = ServerThread(client_socket, self.connections, self.correct_words)

                new_thread.start()  # call run()
                time.sleep(0.09)  # control thread execution order

                self.connections.append(new_thread)

                # update listbox showing connected usernames
                self.listbox.delete(0, tk.END)  # clear all in listbox
                if not self.primary_connected:
                    self.listbox.insert(tk.END, 'Primary not available')
                for x in self.connections:
                    if 'lex' not in x.username:
                        self.listbox.insert(tk.END, x.username)  # insert new data

    def connect_primary(self):
        """
        connect wait push socket to primary server
        """
        add_command = Command()
        add_command.command = 'backup backup_server'
        add_command.payload = 'backup_server'
        try:
            self.wait_push_sock.connect((self.host, self.port1))
            packed_data = pickle.dumps(add_command)
            self.wait_push_sock.sendall(struct.pack('i', len(packed_data)))
            self.wait_push_sock.sendall(packed_data)

            reply_len = struct.unpack("i", self.wait_push_sock.recv(4))[0]
            data = bytearray()
            while reply_len > len(data):
                data += self.wait_push_sock.recv(reply_len - len(data))
            reply_command = pickle.loads(data)  # Receive the server reply
            server_command = reply_command.command.split(" ")
            print('connect wait_push: ', server_command)
            self.listbox.insert(tk.END, 'connected to primary')

        except Exception as e:
            print('Error in add_push: ', e)

        self.wait_push_th = threading.Thread(target=self.wait_push,)
        self.wait_push_th.start()

    def wait_push(self):
        """
        wait primary server push added lexicon
        """
        try:
            while True:
                if self.wait_push_sock.fileno() != -1:
                    a = self.wait_push_sock.recv(4)
                    print("Wanted 4 bytes got " + str(len(a)) + " bytes")

                    if len(a) < 4:
                        raise Exception("client closed socket, ending client thread")

                    message_length = struct.unpack('i', a)[0]
                    print("Message Length: ", message_length)
                    data = bytearray()
                    while message_length > len(data):
                        data += self.wait_push_sock.recv(message_length - len(data))

                    new_command = pickle.loads(data)
                    print("\nCommand is: ", new_command.command.replace('_', ' '))
                    server_command = new_command.command.split(" ")

                    if server_command[0] == "addlexicon":
                        self.correct_words = new_command.payload.split(' ')  # split a str into a list

        except Exception as e:
            print('Error in wait_push: ', e)
            self.primary_connected = False
            self.listbox.insert(tk.END, 'Primary not available')

    def add_lexicon(self):
        while True:
            time.sleep(29)  # time interval
            for conn in self.connections:  # filter lex thread
                if conn.my_socket.fileno() != -1 and 'lex' in conn.username:  # check lexicon socket is good
                    server_command = Command()
                    server_command.command = 'poll'
                    server_command.payload = ''
                    packed_data = pickle.dumps(server_command)  # Serialize the class to a binary array
                    conn.my_socket.sendall(struct.pack("i", len(packed_data)))
                    conn.my_socket.sendall(packed_data)
                    print('send poll: ', conn.username)

    def refresh(self, ):
        """
        update listbox
        https://stackoverflow.com/questions/35861484/how-to-know-the-if-the-socket-connection-is-closed-in-python
        https://www.tutorialspoint.com/python/tk_listbox.htm
        """
        # check username in server, not server_thread; update listbox
        for conn in self.connections:  # for each connection
            if conn.my_socket.fileno() == -1:  # check if socket is closed
                self.connections.remove(conn)  # remove it from connections
        self.listbox.delete(0, tk.END)  # clear all
        for x in self.connections:  # for each connection
            if 'lex' not in x.username:  # exclude lex threads
                self.listbox.insert(tk.END, x.username)  # insert new data

    def check_username(self, new_thread):
        # check username conflict
        usernames = []  # current usernames list
        for cli_thread in self.connections:  # for each connection
            usernames.append(cli_thread.username)  # append existing usernames
        if new_thread.username in usernames:  # check new_thread's username is existed
            reply_command = Command()  # edit reply command
            reply_command.command = 'conflict'  # set command as conflict
            reply_command.payload = new_thread.username  # set payload as username
            packed_data = pickle.dumps(reply_command)  # Serialize the class to a binary array
            # Length of the message is just the length of the array
            new_thread.my_socket.sendall(struct.pack("i", len(packed_data)))  # send data length
            new_thread.my_socket.sendall(packed_data)  # send data
            new_thread.my_socket.close()  # close this thread
            del new_thread
        else:
            self.connections.append(new_thread)  # append new thread to connections

    def exit(self):
        try:  # server exit
            self.server_socket.close()
            self.root.destroy()
            # self.join()
            os._exit(0)

        except Exception as ex:
            print('error in exit: ', ex)


def main():
    """
    backup server
    """
    host = "localhost"  # edit the host address here
    port1 = 7789
    port2 = 9789  # edit the port number

    server2 = Server(host, port1, port2)  # instantiate server object
    server2.start()  # start server thread
    server2.root.mainloop()  # tk mainloop


if __name__ == '__main__':
    main()
