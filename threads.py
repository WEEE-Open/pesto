from typing import Optional
from PyQt5 import uic, QtGui, QtCore
from PyQt5.QtCore import Qt, QEvent, QThread
from utilites import *
import socket
from threading import Thread
from queue import Queue
from pesto import PATH, CURRENT_PLATFORM, warehouse


class Client(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    """
    This is the client thread class. When it is instantiated it create TCP socket that can be used to connect
    the client to the server.
    In the __init__ function the following are initialized:
        - queue: a Queue object that allow the client to interact with other threads
        - socket: the TCP socket
        - host
        - port
    """
    def __init__(self, client_queue: Queue, gui_queue: Queue):
        super(Client, self).__init__()
        self.client_queue = client_queue
        self.gui_queue = gui_queue
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.host = None
        self.port = None
        self.running = False
        self.receiver: Optional[ReceiverThread]
        self.receiver = None

    def connect(self, host: str, port: str):
        """
        When called, try to connect to the host:port combination.
        If the server is not up or is unreachable, it raise the ConnectionRefusedError exception.
        If the connection is established, then it checks if the server send a confirm message: if the message
        arrives it will be put in the queue, else a RuntimeError exception will be raised.
        """
        # noinspection PyBroadException
        try:
            self.running = False
            self.socket.connect((host, int(port)))
            self.running = True
            return True, host, port
        except ConnectionRefusedError:
            print("Connection Refused: Client Unreachable")
            return False, host, port
        except BaseException:
            print("Socket Error: Socket not connected and address not provided when sending on a datagram socket using a sendto call. Request to send or receive data canceled")
            return False, host, port

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
        received = []
        BUFFER = 512
        string = b''
        try:
            while True:
                """ global warehouse is a list that all the unreaded messages from the gui."""
                global warehouse
                """ 
                check if there is a command in the warehouse. If yes, it will be sent to the gui instead of
                 waiting for a new message from server 
                 """
                if len(warehouse) > 0:
                    if b'\r\n' in warehouse[0]:
                        received.append(warehouse[0])
                        del warehouse[0]
                        break
                """ get messages from server (512 byte per iteration) """

                chunk = self.socket.recv(BUFFER)
                chunks = chunk.splitlines(True)
                if len(warehouse) > 0:
                    """ join 2 messages if in the last one in warehouse there is not a newline """
                    if b'\r\n' not in warehouse[-1]:
                        warehouse[-1] += chunks[0]
                        del chunks[0]
                if chunks is None:
                    pass
                else:
                    """ store in warehouse all the messages that are ignored in the iteration """
                    for c in chunks:
                        warehouse.append(c)
                received.append(warehouse[0])
                """ remove the message sent to the gui in the warehouse """
                del warehouse[0]
                if b'\r\n' in received[-1]:
                    break
            """ join all the received chunks to be sent to the gui and decode the byte string """
            received = b''.join(received).decode('utf-8')
            print("SERVER: " + received)
            return received

        except ConnectionAbortedError:
            print("Connection Aborted.")

    def start_receiver(self):
        self.receiver = ReceiverThread(self.client_queue, self)
        self.receiver.start()

    def test_channel(self):
        try:
            self.socket.connect((self.host, int(self.port)))
            return self.ping()
        except:
            return False

    def ping(self):
        try:
            self.send("ping")
            if self.receive() == "pong":
                return True
            return False
        except:
            return False


class UpdatesThread(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, gui_queue: Queue, client_queue: Queue):
        super(UpdatesThread, self).__init__()
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


class ReceiverThread(Thread):
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


class LocalServerThread(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, server_queue: Queue):
        super(LocalServerThread, self).__init__()
        self.server_queue = server_queue
        self.running = True
        self.server = None

    def load_server(self, running: bool):
        if not running:
            self.server = subprocess.Popen(["python", PATH["SERVER"]], stderr=subprocess.PIPE,
                                               stdout=subprocess.PIPE)
            while True:
                output = self.server.stderr.readline().decode('utf-8')
                if "Listening on" in output:
                    self.server_queue.put("SERVER_READY")
                    break
        else:
            self.server_queue.put("SERVER_READY")

    def stop(self):
        self.running = False