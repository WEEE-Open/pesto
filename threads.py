import ctypes
import datetime
import json
import subprocess
import traceback
from typing import Optional

from PyQt5 import uic, QtGui, QtCore
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt, QEvent, QThread
from PyQt5.QtWidgets import QTableWidgetItem, QMenu
from utilites import *
import socket
from threading import Thread
from queue import Queue
import ast
import sys
from multiprocessing import Process
import os
import logging
from pesto import PATH

class Client(Thread):
    """
    This is the client thread class. When it is instantiated it create TCP socket that can be used to connect
    the client to the server.
    In the __init__ function the following are initialized:
        - queue: a Queue object that allow the client to interact with other threads
        - socket: the TCP socket
        - host
        - port
    """
    def __init__(self, queue: Queue, host: str, port: str):
        Thread.__init__(self)
        self.queue = queue
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.host = host
        self.port = int(port)

    def connect(self):
        """
        When called, try to connect to the host:port combination.
        If the server is not up or is unreachable, it raise the ConnectionRefusedError exception.
        If the connection is established, then it checks if the server send a confirm message: if the message
        arrives it will be put in the queue, else a RuntimeError exception will be raised.
        """
        # noinspection PyBroadException
        try:
            self.socket.connect((self.host, self.port))
            return True, self.host, self.port
        except ConnectionRefusedError:
            print("Connection Refused: Client Unreachable")
            return False, self.host, self.port
        except BaseException:
            print("Socket Error: Socket not connected and address not provided when sending on a datagram socket using a sendto call. Request to send or receive data canceled")
            return False, self.host, self.port

    def disconnect(self):
        """
        When called, close socket
        """
        self.socket.close()

    def send(self, msg: str):
        """
        When called, send byte msg to server. For now there is not a maximum lenght limit to the msg.
        The string 'msg' passed to the function will be encoded to a byte string, then the lenght of the message is
        measured to establish the lenght of the byte sequence that must be sent.
        If the number of sent bytes is equal to 0, a RuntimeError will be raised.
        """
        msg += '\r\n'
        msg = msg.encode('utf-8')
        totalsent = 0
        msglen = len(msg)
        while totalsent < msglen:
            sent = self.socket.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket Connection Broken")
            totalsent += sent

    def receive(self):
        """
        When called, return chuncks of text from server.
        The maximum number of bytes that can be received in one transmission is set in the BUFFER variable.
        The function receive a chunk of maximum 512 bytes at time and append the chunk to a list that will be
        returned at the end of the function.
        """
        received = b''
        bytes_recv = 0
        BUFFER = 1
        string = b''
        tmp = b''
        while True:
            chunk = self.socket.recv(BUFFER)
            received += chunk
            bytes_recv += len(chunk)
            tmp += chunk
            if len(tmp) > 2:
                tmp = tmp.decode('utf-8')
                tmp = tmp[1:3]
                tmp= tmp.encode('utf-8')
            if tmp == b'\r\n':
                break
        received = received.decode('utf-8')
        print("SERVER: " + received)
        return received


class GuiBackgroundThread(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, gui_queue: Queue, client_queue: Queue):
        super(GuiBackgroundThread, self).__init__()
        self.gui_queue = gui_queue
        self.client_queue = client_queue
        self.running = True

    def run(self):
        try:
            while self.running:
                data = ""
                if not self.client_queue.empty():
                    data = self.client_queue.get()
                    data: str
                    parts = data.split(' ', 1)
                    cmd = parts[0]
                    if len(parts) > 1:
                        args = parts[1]
                    else:
                        args = ''
                    self.update.emit(cmd, args)
        except KeyboardInterrupt:
            print("Keyboard Interrupt")


class CctfThread(Thread):
    def __init__(self, queue: Queue, client: Client):
        super().__init__()
        self.running = True
        self.client_queue = queue
        self.client = client

    def run(self):
        while self.running:
            data = self.client.receive()
            if data != '':
                self.client_queue.put(data)


class GuiClientThread(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, client_queue: Queue, gui_queue: Queue):
        super(GuiClientThread, self).__init__()
        self.client_queue = client_queue
        self.gui_queue = gui_queue
        self.client: Client
        self.client = None
        self.running = False
        self.receiver: Optional[CctfThread]
        self.receiver = None

    def connect(self, host: str, port: int):
        if self.client is not None:
            self.client.disconnect()
        self.client = Client(queue=self.client_queue, host=host, port=str(port))
        chk, host, port = self.client.connect()
        if chk:
            self.update.emit(f"{host}:{port}", "CONNECTED")
        else:
            message = "Cannot connect to the server.\nTry to restart the application."
            critical_dialog(message, type='ok')
            return
        if not self.running:
            self.receiver = CctfThread(self.client_queue, self.client)
            self.receiver.start()
        self.running = True

    def ping(self):
        self.client.send("ping")
        return self.client.receive()

    def get_disks(self):
        self.client.send("get_disks")

    def erase_disk(self, drive: str):
        self.client.send("queued_badblocks " + drive)

    def disconnect(self):

        self.client.disconnect()


class GuiServerThread(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, server_queue: Queue):
        super(GuiServerThread, self).__init__()
        self.server_queue = server_queue
        self.running = True
        self.server = None

    def start(self):
        self.server = subprocess.Popen(["python", PATH["SERVER"], "--local"], stderr=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
        while True:
            output = self.server.stderr.readline().decode('utf-8')
            if "Listening on" in output:
                self.server_queue.put("SERVER_READY")
                break

    def stop(self):
        if CURRENT_PLATFORM == 'win32':
            self.server.terminate()
        else:
            self.server.terminate()