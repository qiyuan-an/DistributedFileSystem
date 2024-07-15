"""
name: Qiyuan An
id: 1001915560
"""
import socket
import threading
import struct
import pickle
import string
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
    def __init__(self, socket_instance, connections):
        threading.Thread.__init__(self)  # call base constructor
        self.my_socket = socket_instance  # server thread
        # self.username = None
        self.connections = connections  # server connections

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

                new_command = pickle.loads(data)  # pickle loads data
                print("\nCommand is: ", new_command.command.replace('_', ' '))

                client_command = new_command.command.split(" ")
                # Divide the command to recognize it, " " is the divider

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
                    self.spell_check(server_filename)  # do spell check

                    reply_command = Command()
                    reply_command.command = "Uploaded " + server_filename  # edit reply command
                    server_file = open(server_filename, 'rb')  # open modified file
                    reply_command.payload = server_file.read()  # put file to payload
                    server_file.close()  # close file

                elif client_command[0] == 'exit':  # handles client exit
                    reply_command = Command()
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
        """
        correct_words = open("correct.words").readlines()  # open the correct word file
        correct_words = [word.strip() for word in correct_words]  # put correct words in a list
        modified_lines = []  # modified lines placeholder
        f = open(server_filename)  # open received file
        lines = list(f)  # put received file into a list
        f.close()  # close received file
        for i, line in enumerate(lines):  # for each line
            line = line.strip()  # remove the \n
            file_words = line.split()  # split by space
            for j, txt_word in enumerate(file_words):  # for each word in a line
                if txt_word not in correct_words:  # if a word is not in the correct_words list
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
    def __init__(self, host, port):
        """
        https://docs.python.org/3/library/tkinter.html
        https://www.tutorialspoint.com/python/tk_label.htm
        https://www.tutorialspoint.com/python/tk_listbox.htm
        """
        super(Server, self).__init__()
        self.root = tk.Tk()  # tk gui
        self.root.title("Server status")  # set server gui title
        self.root.geometry('250x250')  # set server gui size
        self.frm = tk.Frame(self.root,)  # add frame
        self.connections = []  # list holds client connections
        self.host = host  # host ip
        self.port = port  # host port

        # GUI
        self.frm_m = tk.Frame(self.frm,)  # add middle frame
        self.var = tk.StringVar()  # label content varialbe
        self.label = tk.Label(self.root, textvariable=self.var, relief=tk.RAISED)  # tk label
        self.var.set('Connected usernames')  # set label content
        self.scrollbar = tk.Scrollbar(master=self.frm_m)  # scrollbar to the listbox
        # listbox to display connections
        self.listbox = tk.Listbox(master=self.frm_m, yscrollcommand=self.scrollbar.set,)
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
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # instantiate a socket
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # set reuse socket
        self.server_socket.bind((self.host, self.port))  # bind host address and port
        self.server_socket.listen(1)  # listen for incoming connection
        print("Listening...")

        while True:
            (client_socket, address) = self.server_socket.accept()  # server socket accepting client connection
            print("Incoming connection ",)
            # make a new instance of our thread class to handle requests
            new_thread = ServerThread(client_socket, self.connections)  # instantiate a server thread for connection
            new_thread.start()  # call run()
            time.sleep(0.09)  # control thread execution order

            self.connections.append(new_thread)  # add new thread to connections

            # update listbox showing connected usernames
            self.listbox.delete(0, tk.END)  # clear all in listbox
            for x in self.connections:
                self.listbox.insert(tk.END, x.username)  # insert new data

    def refresh(self,):
        """
        update listbox
        https://stackoverflow.com/questions/35861484/how-to-know-the-if-the-socket-connection-is-closed-in-python
        https://www.tutorialspoint.com/python/tk_listbox.htm
        """
        for cli_thread in self.connections:  # for each connection
            if cli_thread.my_socket.fileno() == -1:  # check if socket is closed
                self.connections.remove(cli_thread)  # remove it from connections
        self.listbox.delete(0, tk.END)  # clear all
        for x in self.connections:  # for each connection
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
        try:
            # server exit
            self.server_socket.close()
            os._exit(0)

        except Exception as ex:
            print('error in exit: ', ex)


def main():
    host = "localhost"  # edit the host address here
    port = 7789  # edit the port number

    server = Server(host, port)  # instantiate serve object
    server.start()  # start server thread
    server.root.mainloop()  # tk mainloop


if __name__ == '__main__':
    main()
