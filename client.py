#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 20 12:35:26 2021

@author: il_palmi

@description: twsited implementation of pinolo.py
"""
import builtins
import json
from twisted.internet import reactor, protocol
from PyQt5.QtCore import QThread
from PyQt5 import QtCore
from twisted.protocols.basic import LineOnlyReceiver

receiver = None


class Client(LineOnlyReceiver):
    """ Qui arrivano i comandi (comunicazione) """

    def lineReceived(self, line):
        try:
            line = line.decode('utf-8')
            self.factory.update_gui(line)
        except UnicodeDecodeError:
            print(f"Oh no, UnicodeDecodeError!")
            return

    def send_msg(self, msg: str):
        self.sendLine(msg.encode("utf-8"))

    def connectionMade(self):
        print("Connected to server.")
        global receiver
        receiver = self
        self.factory.update_gui("connection_made")
        self.send_msg("get_disks")
        self.send_msg("get_queue")

    def disconnect(self):
        try:
            self.transport.loseConnection()
        except builtins.AttributeError as ex:
            if "NoneType" in str(ex):
                print("Trying to disconnect but no connection established.")


class ClientFactory(protocol.ClientFactory):
    """ Qui succedono le cose """

    protocol = Client

    def __init__(self, update_event: QtCore.pyqtSignal, host: str, port: int):
        self.updateEvent = update_event
        self.host = host
        self.port = port
        # WHY ARE YOU RUNNING?
        self.running = False

    def startedConnecting(self, connector):
        print("Connecting.")

    def clientConnectionLost(self, connector, reason):
        print(f"Lost connection. Reason: {reason}")

    def clientConnectionFailed(self, connector, reason):
        print(f"Connection failed. Reason: {reason}")
        d = {"reason": str(reason).replace('\n', '')}
        data = "connection_failed " + json.dumps(d, separators=(',', ':'), indent=None)
        self.update_gui(data)

    def update_gui(self, data):
        data: str
        if data == 'connection_made':
            cmd = data
            args = json.dumps({"host": self.host, "port": str(self.port)})
        else:
            parts = data.split(' ', 1)
            cmd = parts[0]
            if len(parts) > 1:
                args = parts[1]
            else:
                args = ''
        self.updateEvent.emit(cmd, args)


class ReactorThread(QThread):
    updateEvent = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, host: str, port: int):
        QThread.__init__(self)
        self.host = host
        self.port = port
        self.protocol = Client
        self.factory = ClientFactory(self.updateEvent, self.host, self.port)
        self.reactor = reactor

    def run(self) -> None:
        # noinspection PyUnresolvedReferences
        self.reactor.connectTCP(self.host, self.port, self.factory)
        # noinspection PyUnresolvedReferences
        self.reactor.run(installSignalHandlers=False)

    def stop(self):
        # noinspection PyUnresolvedReferences
        self.reactor.callFromThread(Client.disconnect, receiver)

    def reconnect(self, host: str, port: int):
        # noinspection PyUnresolvedReferences
        self.reactor.callFromThread(Client.disconnect, receiver)
        # noinspection PyUnresolvedReferences
        self.reactor.connectTCP(host, port, self.factory)

    def send(self, msg: str):
        # noinspection PyUnresolvedReferences
        self.reactor.callFromThread(Client.send_msg, receiver, msg)


def main():
    host = "127.0.0.1"
    port = 1030
    r_thread = ReactorThread(host, port)
    r_thread.start()
    while True:
        cmd = input("Inserire comando da inviare: ")
        r_thread.send(cmd)


if __name__ == "__main__":
    main()
