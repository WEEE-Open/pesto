#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 20 12:35:26 2021

@author: il_palmi

@description: twsited implementation of pesto.py
"""

from twisted.internet import reactor, protocol
from sys import stdout

""" Qui arrivano i comandi (comunicazione) """
class Client(protocol.Protocol):
    def dataReceived(self, data: bytes):
        stdout.write(data)

    def sendMsg(self, msg: str):
        msg = msg.encode("utf-8")
        msg += b"\r\n"
        self.transport.write(msg)


""" Qui succedono le cose """
class ClientFactory(protocol.ClientFactory):
    protocol = Client

    def __init__(self, app):
        self.app = app

    def startedConnecting(self, connector):
        print("Connecting.")

    def clientConnectionLost(self, connector, reason):
        print(f"Lost connection. Reason: {reason}")

    def clientConnectionFailed(self, connector, reason):
        print(f"Connection failed. Reason: {reason}")


def main():
    host = "127.0.0.1"
    port = 1040


if __name__ == "__main__":
    main()