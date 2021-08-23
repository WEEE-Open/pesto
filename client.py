#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 20 12:35:26 2021

@author: il_palmi

@description: twsited implementation of pinolo.py
"""
import twisted.internet.error
from twisted.internet import reactor, protocol
from threading import Thread
from PyQt5.QtCore import QThread
from PyQt5 import QtCore
from queue import Queue
from twisted.protocols.basic import LineOnlyReceiver

receiver = None
receiverTransport = None

class Client(LineOnlyReceiver):
    """ Qui arrivano i comandi (comunicazione) """

    def lineReceived(self, line):
        try:
            line = line.decode('utf-8')
            self.factory.updateGUI(line)
        except UnicodeDecodeError as e:
            print(f"Oh no, UnicodeDecodeError!")
            return

    def sendMsg(self, msg: str):
        self.sendLine(msg.encode("utf-8"))

    def connectionMade(self):
        print("Connected to server.")
        global receiver
        receiver = self
        receiverTransport = self.transport
        self.sendMsg("get_disks")

    def disconnect(self):
        self.transport.loseConnection()


class ClientFactory(protocol.ClientFactory):
    """ Qui succedono le cose """

    protocol = Client

    def __init__(self, client_queue: Queue, updateEvent: QtCore.pyqtSignal):
        self.client_queue = client_queue
        self.updateEvent = updateEvent
        # WHY ARE YOU RUNNING?
        self.running = False

    def startedConnecting(self, connector):
        print("Connecting.")

    def clientConnectionLost(self, connector, reason):
        print(f"Lost connection. Reason: {reason}")

    def clientConnectionFailed(self, connector, reason):
        print(f"Connection failed. Reason: {reason}")

    def put_in_queue(self, data):
        self.client_queue.put(data)

    def updateGUI(self, data):
        data: str
        parts = data.split(' ', 1)
        cmd = parts[0]
        if len(parts) > 1:
            args = parts[1]
        else:
            args = ''
        self.updateEvent.emit(cmd, args)


class ReactorThread(QThread):
    updateEvent = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, host: str, port: int, client_queue: Queue):
        QThread.__init__(self)
        self.host = host
        self.port = port
        self.client_queue = client_queue
        self.protocol = Client
        self.factory = ClientFactory(self.client_queue, self.updateEvent)
        self.reactor = reactor

    def run(self) -> None:
        self.reactor.connectTCP(self.host, self.port, self.factory)
        self.reactor.run(installSignalHandlers=False)

    def stop(self):
        self.reactor.callFromThread(Client.disconnect, receiver)

    def reconnect(self, host: str, port: int):
        self.reactor.callFromThread(Client.disconnect, receiver)
        self.reactor.connectTCP(host, port, self.factory)

    def send(self, msg: str):
        self.reactor.callFromThread(Client.sendMsg, receiver, msg)


def main():
    host = "127.0.0.1"
    port = 1030
    rThread = ReactorThread(host, port)
    rThread.start()
    while True:
        cmd = input("Inserire comando da inviare: ")
        rThread.send(cmd)


if __name__ == "__main__":
    main()