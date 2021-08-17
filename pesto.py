#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
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

SPACE = 5

REQUIREMENTS = ["Model Family",
                "Device Model",
                "Serial Number",
                "Power_On_Hours",
                "Power_Cycle_Count",
                "SSD_Life_Left",
                "Lifetime_Writes_GiB",
                "Reallocated_Sector_Ct",
                "LU WWN Device Id",
                "Rotation Rate",
                "Current Pending Sector Count",
                "Model Number",
                "Firmware Version"]

SMARTCHECK = ["Power_On_Hours",
              "Reallocated_Sector_Cd",
              "Current Pending Sector Count"]

PATH = {"UI": "/assets/interface.ui",
        "REQUIREMENTS": "/requirements.txt",
        "CRASH": "/crashreport.txt",
        "ASD": "/assets/asd.gif",
        "RELOAD": "/assets/reload.png",
        "PENDING": "/assets/pending.png",
        "ICON": "/assets/icon.png",
        "PROGRESS": "/assets/progress.png",
        "OK": "/assets/ok.png",
        "WARNING": "/assets/warning.png",
        "ERROR": "/assets/error.png",
        "SERVER": "/pesto_server.py"}

QUEUE_TABLE = ["ID",
               "Process",
               "Disk",
               "Status",
               "Progress"
               ]

CLIENT_COMMAND = {"PING": "===PING===",
                  "GET_DISK": "===GET_DISK===",
                  "GET_DISK_WIN": "GET_DISK_WIN",
                  "CONNECT": "===CONNECT==="}

CURRENT_PLATFORM = sys.platform

_sentinel = '===PASS==='


if CURRENT_PLATFORM == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
    for path in PATH:
        PATH[path] = win_path(PATH[path])
else:
    for path in PATH:
        PATH[path] = linux_path(PATH[path])


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


# UI class
class Ui(QtWidgets.QMainWindow):
    def __init__(self, gui_queue: Queue, client_queue: Queue, server_queue: Queue):
        super(Ui, self).__init__()
        uic.loadUi(PATH["UI"], self)
        self.gui_queue = gui_queue
        self.client_queue = client_queue
        self.server_queue = server_queue
        self.running = True

        self.find_items()
        self.show()
        self.bg_thread = GuiBackgroundThread(self.gui_queue, self.client_queue)
        self.client_thread = GuiClientThread(self.client_queue, self.gui_queue)
        self.server = GuiServerThread(self.server_queue)
        self.server.start()
        while True:
            if self.server_queue.get() == "SERVER_READY":
                break
        self.bg_thread.start()
        self.client_thread.start()

        self.bg_thread.update.connect(self.gui_update)
        self.client_thread.update.connect(self.client_updates)
        self.setup()

    def find_items(self):
        # set icon
        self.setWindowIcon(QIcon(PATH["ICON"]))

        # get latest configuration
        self.latest_conf()

        # disks table
        self.diskTable = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.diskTable.setHorizontalHeaderItem(0, QTableWidgetItem("Drive"))
        self.diskTable.setHorizontalHeaderItem(1, QTableWidgetItem("Dimension"))
        self.diskTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.diskTable.setColumnWidth(0, 77)
        self.diskTable.horizontalHeader().setStretchLastSection(True)

        # queue table
        self.queueTable = self.findChild(QtWidgets.QTableWidget, 'queueTable')
        self.queueTable.setRowCount(0)
        table_setup(self.queueTable, QUEUE_TABLE)

        # reload button
        self.reloadButton = self.findChild(QtWidgets.QPushButton, 'reloadButton')
        self.reloadButton.clicked.connect(self.refresh)
        self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))

        # erase button
        self.eraseButton = self.findChild(QtWidgets.QPushButton, 'eraseButton')
        self.eraseButton.clicked.connect(self.erase)

        # smart button
        self.smartButton = self.findChild(QtWidgets.QPushButton, 'smartButton')
        self.smartButton.clicked.connect(self.smart)

        # cannolo button
        self.cannoloButton = self.findChild(QtWidgets.QPushButton, 'cannoloButton')
        self.cannoloButton.clicked.connect(self.cannolo)

        # text field
        self.textField = self.findChild(QtWidgets.QTextEdit, 'textEdit')
        self.textField.setReadOnly(True)
        font = self.textField.document().defaultFont()
        font.setFamily("Monospace")
        font.setStyleHint(QtGui.QFont.Monospace)
        self.textField.document().setDefaultFont(font)
        self.textField.setCurrentFont(font)
        self.textField.setFontPointSize(10)

        # local radio button
        self.localRadioBtn = self.findChild(QtWidgets.QRadioButton, 'localRadioBtn')
        if not self.remoteMode:
            self.localRadioBtn.setChecked(True)
        self.localRadioBtn.clicked.connect(self.set_remote_mode)

        # remote radio button
        self.remoteRadioBtn = self.findChild(QtWidgets.QRadioButton, 'remoteRadioBtn')
        if self.remoteMode:
            self.remoteRadioBtn.setChecked(True)
        self.remoteRadioBtn.clicked.connect(self.set_remote_mode)

        # remoteIp input
        self.hostInput = self.findChild(QtWidgets.QLineEdit, 'remoteIp')
        self.hostInput.setText(self.host)


        # remotePort input
        self.portInput = self.findChild(QtWidgets.QLineEdit, 'remotePort')
        if self.port != None:
            self.portInput.setText(str(self.port))

        # restore button
        self.restoreButton = self.findChild(QtWidgets.QPushButton, "restoreButton")
        self.restoreButton.clicked.connect(self.restore)

        # default values button
        self.defaultButton = self.findChild(QtWidgets.QPushButton, "defaultButton")
        self.defaultButton.clicked.connect(self.default_config)

        # remove config button
        self.defaultButton = self.findChild(QtWidgets.QPushButton, "removeButton")
        self.defaultButton.clicked.connect(self.remove_config)

        # save config button
        self.saveButton = self.findChild(QtWidgets.QPushButton, "saveButton")
        self.saveButton.clicked.connect(self.save_config)

        # configuration list
        self.ipList = self.findChild(QtWidgets.QListWidget, "ipList")
        for key in self.settings.childKeys():
            if "saved" in key:
                values = self.settings.value(key)
                self.ipList.addItem(values[0])
        self.ipList.clicked.connect(self.load_config)

        # find button
        self.findButton = self.findChild(QtWidgets.QPushButton, "findButton")
        self.findButton.clicked.connect(self.find_directory)
        if self.remoteMode:
            self.findButton.setEnabled(False)

        # directory text
        self.directoryText = self.findChild(QtWidgets.QLineEdit, "directoryText")
        for key in self.settings.childKeys():
            if "cannoloDir" in key:
                self.directoryText.setText(str(self.settings.value(key)))
        if self.remoteMode:
            self.directoryText.setReadOnly(False)

        # cannolo label
        self.cannoloLabel = self.findChild(QtWidgets.QLabel, "cannoloLabel")
        self.cannoloLabel.setStyleSheet('color: blue')
        if self.remoteMode:
            self.cannoloLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")
        else:
            self.cannoloLabel.setText("")

        # asd tab
        self.asdLabel = self.findChild(QtWidgets.QLabel, "asdLabel")
        self.gif = QMovie(PATH["ASD"])
        self.asdLabel.setMovie(self.gif)
        self.gif.start()

    def latest_conf(self):
        self.settings = QtCore.QSettings("WEEE-Open", "PESTO")
        self.remoteMode = self.settings.value("remoteMode")
        if self.remoteMode == 'False':
            self.remoteMode = False
            self.host = "127.0.0.1"
            self.port = 1030
        else:
            self.remoteMode = True
            try:
                self.host = self.settings.value("remoteIp")
                self.queue.put("host=" + str(self.host))
                self.port = self.settings.value("remotePort")
                self.queue.put("port=" + str(self.port))
            except ValueError:
                self.port = None

    def setup(self):
        self.set_remote_mode()

        # check if the host and port field are set
        if self.host == None and self.port == None:
            message = "The host and port combination is not set.\nPlease vist the settings section."
            warning_dialog(message,'ok')

        # connect to server
        self.client_thread.connect(self.host, self.port)

        # get disks list
        self.client_thread.get_disks()

    def eventFilter(self, source: 'QObject', event: 'QEvent'):
        selectedRow = self.queueTable.currentRow()
        if event.type() == QEvent.ContextMenu and source is self.queueTable and selectedRow != -1:
            menu = QMenu()
            menu.addAction("Stop", self.stop_dialog)
            menu.addAction("Remove", self.remove_dialog)
            menu.addAction("Log")
            menu.addAction("Info", self.info_dialog)
            menu.exec_(event.globalPos())
            return True
        return super().eventFilter(source, event)

    def stop_dialog(self):
        id = self.queueTable.cellWidget(self.queueTable.currentRow(), 0).text()
        message = 'Do you want to stop the process?\nID: ' + id
        if warning_dialog(message, type='yes_no') == QtWidgets.QMessageBox.Yes:
            icon = self.queueTable.cellWidget(self.queueTable.currentRow(), 3)
            icon.setPixmap(QtGui.QPixmap(PATH["ERROR"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))

    def remove_dialog(self):
        id = self.queueTable.cellWidget(self.queueTable.currentRow(), 0).text()
        message = 'With this action you will also stop the process (ID: '+ id + ")\n"
        message += 'Do you want to proceed?'
        if warning_dialog(message, type='yes_no') == QtWidgets.QMessageBox.Yes:
            self.queueTable.removeRow(self.queueTable.currentRow())

    def info_dialog(self):
        process = self.queueTable.cellWidget(self.queueTable.currentRow(), 1).text()
        message = ''
        if process == "Smart check":
            message += "Process type: " + process + "\n"
            message += "Get SMART data from the selected drive\n"
            message += "and print the output to the console."
        elif process == "Erase":
            message += "Process type: " + process + "\n"
            message += "Wipe off all data in the selected drive."
        info_dialog(message)

    def erase(self):
        try:
            selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if selected_drive is None:
                return
            else:
                selected_drive = selected_drive.text()
            message = "Do you want to wipe all disk's data?\nDisk: " + selected_drive
            if critical_dialog(message, type='yes_no') != QtWidgets.QMessageBox.Yes:
                return
            self.textField.clear()
            self.update_queue(drive=selected_drive, mode="erase")
            self.client_thread.erase_disk(selected_drive)

        except Exception:
            print(traceback.print_exc(Exception))

    def smart(self):
        try:
            selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0).text()
            self.update_queue(drive=selected_drive, mode="smart")
        except AttributeError:
            selected_drive = None

        if selected_drive is None:
            message = "There are no selected drives."
            warning_dialog(message, type='ok')
            return
        # clear console
        self.textField.clear()

        # get data and maximum length of entry for better output
        #data, maximum = smart_parser(selected_drive, self.remoteMode, platform=CURRENT_PLATFORM,
         #                            requirements=REQUIREMENTS)
        text = data_output(data, maximum)
        text = smart_analyzer(data, text)
        for line in text:
            if "SMART DATA CHECK" in line:
                if "OLD" in line:
                    self.textField.setTextColor(QtGui.QColor("blue"))
                    self.textField.append("\n" + line)
                    self.textField.setTextColor(QtGui.QColor("black"))
                elif "FAIL" in line:
                    self.textField.setTextColor(QtGui.QColor("red"))
                    self.textField.append("\n" + line)
                    self.textField.setTextColor(QtGui.QColor("black"))
                elif "OK" in line:
                    self.textField.setTextColor(QtGui.QColor("green"))
                    self.textField.append("\n" + line)
                    self.textField.setTextColor(QtGui.QColor("black"))
            else:
                self.textField.append(line)

    def cannolo(self):
        selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0).text()
        message = "Do you want to load a fresh system installation in disk " + selected_drive + "?"
        if warning_dialog(message, type='yes_no') != QtWidgets.QMessageBox.Yes:
            self.client_thread.ping()
        self.textField.clear()
        if self.remoteMode:
            cmd = 'cannolo ' + selected_drive
            data = None
            self.textField.append(data)
            self.update_queue(drive=selected_drive, mode="cannolo")
        else:
            self.textField.append("Sto cannolando il disco " + selected_drive)
            self.update_queue(drive=selected_drive, mode="cannolo")

    def set_remote_mode(self):
        if self.localRadioBtn.isChecked():
            self.remoteMode = False
            self.remoteMode = False
            self.settings.setValue("latestHost", self.host)
            self.settings.setValue("latestPort", self.port)
            self.host = "127.0.0.1"
            self.port = 1030
            self.hostInput.setReadOnly(True)
            self.portInput.setReadOnly(True)
            self.saveButton.setEnabled(False)
            self.findButton.setEnabled(True)
            self.directoryText.setReadOnly(True)
            self.cannoloLabel.setText("")
        elif self.remoteRadioBtn.isChecked():
            self.remoteMode = True
            self.host = self.settings.value("latestHost")
            self.port = str(self.settings.value("latestPort"))
            self.hostInput.setReadOnly(False)
            self.hostInput.setText(self.host)
            self.portInput.setReadOnly(False)
            self.portInput.setText(self.port)
            self.saveButton.setEnabled(True)
            self.findButton.setEnabled(False)
            self.directoryText.setReadOnly(False)
            self.cannoloLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")

    def refresh(self):
        self.host = self.hostInput.text()
        self.port = int(self.portInput.text())
        self.setup()

    def restore(self):
        self.hostInput.setText(self.host)
        self.portInput.setText(str(self.port))

    def update_queue(self, drive, mode):
        #self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        row = self.queueTable.rowCount()
        self.queueTable.insertRow(row)
        for idx, entry in enumerate(QUEUE_TABLE):
            label = object()
            if entry == "ID":  # ID
                t = datetime.datetime.now()
                t = t.strftime("%d%m%y-%H%M%S")
                label = t
            if entry == "Process":  # PROCESS
                if mode == 'erase':
                    label = "Erase"
                elif mode == 'smart':
                    label = "Smart check"
                elif mode == 'cannolo':
                    label = "Cannolo"
            if entry == "Disk":  # DISK
                label = drive
            if entry == "Status":  # STATUS
                if self.queueTable.rowCount() != 0:
                    label = QtWidgets.QLabel()
                    label.setPixmap(QtGui.QPixmap(PATH["PENDING"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
                else:
                    label.setPixmap(QtGui.QPixmap(PATH["PROGRESS"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
            if entry == "Progress":  # PROGRESS
                label = QtWidgets.QProgressBar()
                label.setValue(0)


            if entry in ["ID", "Process", "Disk"]:
                label = QTableWidgetItem(label)
                label.setTextAlignment(Qt.AlignCenter)
                self.queueTable.setItem(row, idx, label)
            else:
                label.setAlignment(Qt.AlignCenter)
                self.queueTable.setCellWidget(row, idx, label)

    def save_config(self):
        ip = self.hostInput.text()
        port = self.portInput.text()
        if self.ipList.findItems(ip, Qt.MatchExactly):
            message = "Do you want to overwrite the old configuration?"
            if warning_dialog(message, type='yes_no') == QtWidgets.QMessageBox.Yes:
                self.settings.setValue("saved-" + ip, [ip, port])
        else:
            self.ipList.addItem(ip)
            self.settings.setValue("saved-" + ip, [ip, port])

    def remove_config(self):
        ip = self.ipList.currentItem().text()
        message = "Do you want to remove the selected configuration?"
        if warning_dialog(message, type='yes_no') == QtWidgets.QMessageBox.Yes:
            for key in self.settings.childKeys():
                if ip in key:
                    self.ipList.takeItem(self.ipList.row(self.ipList.currentItem()))
                    self.settings.remove(key)

    def load_config(self):
        ip = self.ipList.currentItem().text()
        for key in self.settings.childKeys():
            if ip in key:
                values = self.settings.value(key)
                port = values[1]
                self.hostInput.setText(ip)
                self.portInput.setText(port)

    def default_config(self):
        message = "Do you want to restore all settings to default?\nThis action is unrevocable."
        if critical_dialog(message, "yes_no") == QtWidgets.QMessageBox.Yes:
            self.settings.clear()
            self.ipList.clear()
            self.setup()

    def find_directory(self):
        dialog = QtWidgets.QFileDialog()
        dir = dialog.getExistingDirectory(self, "Open Directory", "/home", QtWidgets.QFileDialog.ShowDirsOnly)
        self.directoryText.setText(dir)

    def client_updates(self, text, type):
        if type == 'CONNECTED':
            self.statusBar().showMessage(f"Connected to {text}")

        elif type == 'PING':
            self.statusBar().showMessage(text)

        elif type == 'LIST_DISKS':
            drives = text
            if drives is None:
                self.diskTable.clear()
                self.diskTable.setRowCount(0)
                return

            # compile disks table with disks list
            for row, d in enumerate(drives):
                self.diskTable.setRowCount(row + 1)
                self.diskTable.setItem(row, 0, QTableWidgetItem(d[0]))
                if sys.platform == 'win32':
                    self.diskTable.setItem(row, 1, QTableWidgetItem(str(int(float(d[1]) / 1000000000)) + " GiB"))
                else:
                    self.diskTable.setItem(row, 1, QTableWidgetItem(d[1]))

        elif type == 'sessionTerminated':
            self.statusBar().showMessage("Terminating Program")

    def gui_update(self, cmd: str, params: str):
        try:
            params = json.loads(params)
        except json.decoder.JSONDecodeError:
            print("Expected JSON, exception ignored.")
        # cmd = get_disks
        # params = [{ ... }, { ... }, ...]

        # stringone: get_disks [{schifo:lezzo}{...}]
        if cmd == 'queue_status':
            for row in range(self.queueTable.rowCount()):
                if self.queueTable.item(row, 2).text() == params["target"]:
                    progressBar = self.queueTable.cellWidget(row, 4)
                    progressBar.setValue(int(params["percentage"]))
                    if int(params["percentage"]) == 100:
                        message = "Operazione completata"
                        status = self.queueTable.cellWidget(row, 3)
                        status.setPixmap(QtGui.QPixmap(PATH["OK"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
                        info_dialog(message)

        elif cmd == 'get_disks':
            drives = params
            if len(drives) <= 0:
                self.diskTable.clear()
                self.diskTable.setRowCount(0)
                return
            # compile disks table with disks list
            rows = 0
            for d in drives:
                if "[BOOT]" in d["mountpoint"]:
                    continue
                rows += 1
                self.diskTable.setRowCount(rows)
                if sys.platform == 'win32':
                    self.diskTable.setItem(rows - 1, 0, QTableWidgetItem("Disk " + d["path"]))
                else:
                    self.diskTable.setItem(rows - 1, 0, QTableWidgetItem(d["path"]))
                self.diskTable.setItem(rows - 1, 1, QTableWidgetItem(str(int(int(d["size"]) / 1000000000)) + " GB"))

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("remoteMode", str(self.remoteMode))
        self.settings.setValue("remoteIp", self.hostInput.text())
        self.settings.setValue("remotePort", self.portInput.text())
        self.settings.setValue("cannoloDir", self.directoryText.text())
        self.server.stop()


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


def main():
    try:
        check_requirements(PATH["REQUIREMENTS"])
        queue = Queue()
        gui_bg_queue = Queue()
        client_queue = Queue()
        server_queue = Queue()
        app = QtWidgets.QApplication(sys.argv)
        window = Ui(gui_bg_queue, client_queue, server_queue)
        app.exec_()
        input()

    except KeyboardInterrupt:
        print("KeyboardInterrupt")

    except Exception:
        print(traceback.print_exc(file=sys.stdout))
        input()


if __name__ == "__main__":
    main()
