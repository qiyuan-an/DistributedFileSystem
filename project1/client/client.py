"""
Pr 1
Client
"""
import socket
import struct
import pickle
import string
import os
import tkinter as tk
from tkinter.filedialog import askopenfilename


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
    def __init__(self, host, port):
        self.host = host  # host address
        self.port = port  # host port number
        self.root = tk.Tk()  # use tk as gui
        self.root.title("File transfer")  # tk gui's title
        self.frm = tk.Frame(self.root)  # tk frame
        self.sock = None  # client socket
        self.username = None  # client username

        # Mid
        self.frm_M = tk.Frame(self.frm)  # middle frame
        self.scrollbar = tk.Scrollbar(master=self.frm_M)  # scrollbar for listbox
        self.listbox = tk.Listbox(  # listbox for display
            master=self.frm_M,
            yscrollcommand=self.scrollbar.set
        )
        # pack gui components
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=False)
        self.listbox.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        text_input = tk.Entry(master=self.frm_M)
        text_input.pack(expand=True)
        text_input.bind("<Return>", lambda x: self.connect(text_input))  # bind text input to connect function
        # connect, upload, exit buttons
        tk.Button(self.frm_M, text='Connect', command=lambda: self.connect(text_input), width=15).pack(side=tk.TOP)
        tk.Button(self.frm_M, text='Upload', command=self.upload, width=15).pack(side=tk.TOP)
        tk.Button(self.frm_M, text='Exit', command=self.exit, width=15).pack(side=tk.TOP)
        self.frm_M.pack(side=tk.LEFT)
        self.frm.pack()

    def connect(self, text_input):  # connect client to server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # instantiate a socket
        self.sock.connect((self.host, self.port))  # connect socket to host address and port
        self.username = text_input.get()  # get username from user input
        text_input.delete(0, tk.END)  # clear text input
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
                self.listbox.insert(1, f'{username} connected')  # insert username connected
            elif server_command[0] == 'conflict':  # when server echoed username conflict
                username = reply_command.payload  # get username from payload
                self.listbox.delete(0, tk.END)  # clear listbox
                self.listbox.insert(1, f'{username} conflicted')  # insert username conflict

        except Exception as e:  # print exception
            print('Error in connect: ', e)

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
            reply_command = pickle.loads(data)  # pickle loads received data

            server_command = reply_command.command.split(" ")  # parse reply command
            if server_command[0] == "Uploaded":  # when server returned uploaded file
                server_filename = server_command[1]  # get server returned filename
                self.listbox.insert(2, "Server echoed file: ", server_filename)  # put this msg into listbox
                server_file = open(server_filename, 'wb')  # open the received file
                server_file.write(reply_command.payload)  # write payload to file content
                server_file.close()  # close file handler
                return server_filename

        except Exception as e:  # print exception
            print("Error in upload: ", e)

    def exit(self):
        try:
            # client send exit message
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
            self.listbox.insert(3, "server echoed: ", reply_command.payload)  # update listbox
            # close client socket and thread
            self.sock.close()
            os._exit(0)

        except Exception as ex:  # print exception
            print('error in exit: ', ex)


def main():
    # host address and port #, should be the same as the server
    host = "localhost"
    port = 7789

    root = Application(host, port)  # instantiate a client
    tk.mainloop()  # client tk gui mainloop

    root.sock.close()  # close the client socket


if __name__ == '__main__':
    main()
