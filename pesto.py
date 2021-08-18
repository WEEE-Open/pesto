#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
import json
import traceback
import logging
import sys
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QMenu
from threads import *

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
        "SERVER": "/pesto_server.py",
        "LOGFILE": "/tmp/crashreport.py"}

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

initialize_path(CURRENT_PLATFORM, PATH)

logging.basicConfig(level=logging.DEBUG, filename=PATH["LOGFILE"])

warehouse = []

# UI class
class Ui(QtWidgets.QMainWindow):
    def __init__(self, gui_queue: Queue, client_queue: Queue, server_queue: Queue) -> None:
        super(Ui, self).__init__()
        uic.loadUi(PATH["UI"], self)
        self.gui_queue = gui_queue          # Command queue for gui
        self.client_queue = client_queue    # Command queue for client
        self.server_queue = server_queue    # Command queue for server
        self.running = True
        self.server_ready = False

        """ Defining all items in GUI """
        self.diskTable = None
        self.queueTable = None
        self.reloadButton = None
        self.eraseButton = None
        self.smartButton = None
        self.cannoloButton = None
        self.textField = None
        self.localRadioBtn = None
        self.remoteRadioBtn = None
        self.hostInput = None
        self.portInput = None
        self.restoreButton = None
        self.defaultButton = None
        self.saveButton = None
        self.ipList = None
        self.findButton = None
        self.cannoloLabel = None
        self.directoryText = None
        self.asdLabel = None
        self.gif = None
        self.settings = None
        self.host = None
        self.port = None
        self.remoteMode = None

        """ Initialization operations """
        self.find_items()
        self.show()
        self.gui_thread = UpdatesThread(self.gui_queue, self.client_queue)
        self.client_thread = Client(self.client_queue, self.gui_queue)
        self.server_thread = LocalServerThread(self.server_queue)
        self.client_thread.start()
        self.server_thread.start()
        self.gui_thread.start()
        self.gui_thread.update.connect(self.gui_update)         # GUI thread signals
        self.client_thread.update.connect(self.client_updates)  # client thread signals
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
        if self.port is not None:
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
        if self.host is None and self.port is None:
            message = "The host and port combination is not set.\nPlease visit the settings section."
            warning_dialog(message, 'ok')

        # check if server alive
        if self.client_thread.test_channel():
            print("found background server")
            self.server_thread.load_server(running=True)
        else:
            print("server not running")
            self.server_thread.load_server(running=False)
        if not CURRENT_PLATFORM == 'win32':
            while True:
                if self.server_queue.get() == "SERVER_READY":
                    self.client_thread.connect(self.host, self.port)
                    break
        else:
            self.client_thread.connect(self.host, self.port)
        # get disks list
        self.client_thread.start_receiver()

        self.client_thread.send("get_disks")

    def eventFilter(self, source: 'QObject', event: 'QEvent'):
        selected_row = self.queueTable.currentRow()
        if event.type() == QEvent.ContextMenu and source is self.queueTable and selected_row != -1:
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
        message = 'With this action you will also stop the process (ID: ' + id + ")\n"
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
                selected_drive = selected_drive.text().lstrip("Disk ")
            message = "Do you want to wipe all disk's data?\nDisk: " + selected_drive
            if critical_dialog(message, type='yes_no') != QtWidgets.QMessageBox.Yes:
                return
            self.textField.clear()
            self.client_thread.send("queued_badblocks " + selected_drive)

        except Exception:
            print(traceback.print_exc(Exception))

    def smart(self):
        try:
            selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if selected_drive is None:
                message = "There are no selected drives."
                warning_dialog(message, type='ok')
                return
            self.textField.clear()
            drive = selected_drive.text().lstrip("Disk ")
            self.client_thread.send("queued_smartctl " + drive)

        except:
            print(traceback.print_exc(file=sys.stdout))

    def cannolo(self):
        selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0).text()
        message = "Do you want to load a fresh system installation in disk " + selected_drive + "?"
        if warning_dialog(message, type='yes_no') != QtWidgets.QMessageBox.Yes:
            self.client_thread.test_channel()
        self.update_queue(drive=selected_drive, mode="cannolo")

    def set_remote_mode(self):
        if CURRENT_PLATFORM == 'win32':
            self.remoteRadioBtn.setChecked(True)
            self.localRadioBtn.setCheckable(False)
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
        self.client_thread.send("get_disks")

    def restore(self):
        self.hostInput.setText(self.host)
        self.portInput.setText(str(self.port))

    def update_queue(self, id, drive, mode):
        # self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        row = self.queueTable.rowCount()
        self.queueTable.insertRow(row)
        for idx, entry in enumerate(QUEUE_TABLE):
            label = object()
            if entry == "ID":  # ID
                label = id
            elif entry == "Process":  # PROCESS
                if mode == 'queued_badblocks':
                    label = "Erase"
                elif mode == 'queued_smartctl' or mode == 'smartctl':
                    label = "Smart check"
                elif mode == 'cannolo':
                    label = "Cannolo"
                else:
                    label = "Unknown"
            elif entry == "Disk":  # DISK
                label = drive
            elif entry == "Status":  # STATUS
                if self.queueTable.rowCount() != 0:
                    label = QtWidgets.QLabel()
                    label.setPixmap(QtGui.QPixmap(PATH["PENDING"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
                else:
                    label.setPixmap(QtGui.QPixmap(PATH["PROGRESS"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
            elif entry == "Progress":  # PROGRESS
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
        """
        Typical param str is:
            cmd [{param_1: 'text'}, {param_2: 'text'}, {param_3: 'text'}, ...]
        Possible cmd are:
            get_disks --> drives information for disks table
            queue_status --> Information about badblocks process

        """
        try:
            params = json.loads(params)
        except json.decoder.JSONDecodeError:
            print(f"Ignored exception, expected JSON but this isn't: {params}")

        if cmd == 'queue_status':
            row = 0
            rows = self.queueTable.rowCount()
            for row in range(rows + 1):
                # Check if we already have that id
                item = self.queueTable.item(row, 0)
                if item is not None and item.text() == params["id"]:
                    # print("found " + params["id"] + " on line " + str(row))
                    break
                elif item is None:
                    self.update_queue(id=params["id"], drive=params["target"], mode=params["command"])
                    # print("added row " + str(row))
                    rows += 1
            progress_bar = self.queueTable.cellWidget(row, 4)
            progress_bar.setValue(int(params["percentage"]))
            if int(params["percentage"]) == 100:
                status = self.queueTable.cellWidget(row, 3)
                status.setPixmap(QtGui.QPixmap(PATH["OK"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))

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

        elif cmd == 'smartctl' or cmd == 'queued_smartctl':
            text = []
            text.append("Drive: " + params["disk"])
            text.append("########################")
            text.append("Smartctl output:\n " + params["output"])
            for line in text:
                self.textField.append(line)

        elif cmd == 'pong':
            self.server_ready = True

    def closeEvent(self):
        self.settings.setValue("remoteMode", str(self.remoteMode))
        self.settings.setValue("remoteIp", self.hostInput.text())
        self.settings.setValue("remotePort", self.portInput.text())
        self.settings.setValue("cannoloDir", self.directoryText.text())
        self.client_thread.disconnect()
        sys.exit(0)


def main():
    try:
        check_requirements(PATH["REQUIREMENTS"])
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
        logging.exception(traceback.print_exc(file=sys.stdout))


if __name__ == "__main__":
    main()
