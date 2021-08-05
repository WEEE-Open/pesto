#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
import socket
import subprocess
import paramiko
import sys
import ctypes
import datetime
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt, QEvent, QObject
from PyQt5.QtWidgets import QTableWidgetItem, QMenu
from utilites import win_path, check_requirements, SshSession, data_output, error_dialog, info_dialog, warning_dialog

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
                "Current Pending Sector Count"]

SMARTCHECK = ["Power_On_Hours",
              "Reallocated_Sector_Cd",
              "Current Pending Sector Count"]

BLUE = "\033[36;40m"
RED = "\033[31;40m"
END_ESCAPE = "\033[0;0m"

IP = '192.168.2.3'
USER = 'piall'
PASSWD = 'asd'

CURRENT_PLATFORM = sys.platform

UI_PATH = "/assets/interface.ui"
ARROW_PATH = "/assets/arrow.png"


def main():
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = Ui()
        app.exec_()

    except KeyboardInterrupt:
        print("Ok ciao")
    # input("Premere INVIO per uscire ...")


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        if CURRENT_PLATFORM == 'win32':
            uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + win_path(UI_PATH), self)
        else:
            uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + UI_PATH, self)

        # get latest configuration
        self.settings = QtCore.QSettings("WEEE-Open", "PESTO")
        self.remoteMode = self.settings.value("conf/remoteMode")
        if self.remoteMode == 'False':
            self.remoteMode = False
        else:
            self.remoteMode = True
        self.sshIp = self.settings.value("conf/sshIp")
        self.sshUser = self.settings.value("conf/sshUser")
        self.sshPasswd = self.settings.value("conf/sshPasswd")

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
        for idx, label in enumerate(QUEUE_TABLE):
            self.queueTable.setHorizontalHeaderItem(idx, QTableWidgetItem(label))
        self.queueTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.queueTable.setColumnWidth(2, 50)
        self.queueTable.setColumnWidth(3,50)
        self.queueTable.horizontalHeader().setStretchLastSection(True)
        self.queueTable.installEventFilter(self)

        # reload button
        self.reloadButton = self.findChild(QtWidgets.QPushButton, 'reloadButton')
        self.reloadButton.clicked.connect(self.refresh)
        self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))

        # erase button
        self.eraseButton = self.findChild(QtWidgets.QPushButton, 'eraseButton')
        self.eraseButton.clicked.connect(self.erase_dialog)

        # smart button
        self.smartButton = self.findChild(QtWidgets.QPushButton, 'smartButton')
        self.smartButton.clicked.connect(self.smart)

        # text field
        self.textField = self.findChild(QtWidgets.QTextEdit, 'textEdit')
        self.textField.setReadOnly(True)
        self.textField.setCurrentFont(QtGui.QFont("Monospace"))
        self.textField.setFontPointSize(10)

        # radio buttons group box
        self.radioGroupBox = self.findChild(QtWidgets.QGroupBox, 'radioGroupBox')

        # local radio button
        self.localRadioBtn = self.findChild(QtWidgets.QRadioButton, 'localRadioBtn')
        if not self.remoteMode:
            self.localRadioBtn.setChecked(True)
        self.localRadioBtn.clicked.connect(self.set_remote_mode)

        # ssh radio button
        self.sshRadioBtn = self.findChild(QtWidgets.QRadioButton, 'sshRadioBtn')
        if self.remoteMode:
            self.sshRadioBtn.setChecked(True)
        self.sshRadioBtn.clicked.connect(self.set_remote_mode)

        # sshIp input
        self.sshIpInput = self.findChild(QtWidgets.QLineEdit, 'sshIp')
        self.sshIpInput.setText(self.sshIp)

        # sshUser input
        self.sshUserInput = self.findChild(QtWidgets.QLineEdit, 'sshUser')
        self.sshUserInput.setText(self.sshUser)

        # sshUser input
        self.sshPasswdInput = self.findChild(QtWidgets.QLineEdit, 'sshPasswd')
        self.sshPasswdInput.setText(self.sshPasswd)

        # refresh button
        self.refreshButton = self.findChild(QtWidgets.QPushButton, "refreshButton")
        self.refreshButton.clicked.connect(self.refresh)

        # restore button
        self.restoreButton = self.findChild(QtWidgets.QPushButton, "restoreButton")
        self.restoreButton.clicked.connect(self.restore)

        # default values button
        self.defaultButton = self.findChild(QtWidgets.QPushButton, "defaultButton")
        self.defaultButton.clicked.connect(self.default_dialog)

        # save button
        self.saveButton = self.findChild(QtWidgets.QPushButton, "saveButton")
        self.saveButton.clicked.connect(self.save_ip)

        # ip list
        self.ipList = self.findChild(QtWidgets.QListWidget, "ipList")

        # asd tab
        self.asdLabel = self.findChild(QtWidgets.QLabel, "asdLabel")
        self.gif = QMovie(PATH["ASD"])
        self.asdLabel.setMovie(self.gif)
        self.gif.start()

        self.setup()
        self.show()

    def setup(self):
        # ssh session initialization
        if self.remoteMode:
            ssh = SshSession(self.sshIp, self.sshUser, self.sshPasswd)
            if not ssh.initialize():
                self.remoteMode = False
                self.localRadioBtn.setChecked(True)
                return
            drives = get_disks(ssh)  # get lsblk results
            ssh.kill()
        else:
            drives = local_setup(sys.platform)

        if drives is None:
            self.table.clear()
            self.table.setRowCount(0)
            return

        for row, d in enumerate(drives):
            self.table.setRowCount(row+1)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(d[0]))
            if sys.platform == 'win32':
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(int(float(d[1])/1000000000)) + " GiB"))
            else:
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(d[1]))

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

    def erase_dialog(self):
        if self.diskTable.currentItem() is None:
            return
        message = "Are you sure about that?"
        yes_no_dialog(message=message, yes_function=self.erase, no_function=None)

    def default_dialog(self):
        message = "Do you want to restore all settings to default?\nThis action is irrevocable."
        yes_no_dialog(message=message, yes_function=self.default, no_function=None)

    def remove_dialog(self):
        id = self.queueTable.cellWidget(self.queueTable.currentRow(), 0).text()
        message = 'With this action you will also stop the process (ID: '+ id + ")\n"
        message += 'Do you want to proceed?'
        if warning_dialog(message) == QtWidgets.QMessageBox.Yes:
            self.queueTable.removeRow(self.queueTable.currentRow())

    def stop_dialog(self):
        id = self.queueTable.cellWidget(self.queueTable.currentRow(), 0).text()
        message = 'Do you want to stop the process?\nID: ' + id
        if warning_dialog(message) == QtWidgets.QMessageBox.Yes:
            icon = self.queueTable.cellWidget(self.queueTable.currentRow(), 3)
            icon.setPixmap(QtGui.QPixmap(PATH["ERROR"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))

    def erase(self):
        selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0).text()
        self.textField.clear()
        self.textField.append("Sto piallando il disco " + selected_drive)
        self.update_queue(drive=selected_drive, mode="erase")

    def smart(self):
        selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0).text()
        self.update_queue(drive=selected_drive, mode="smart")
        if selected_drive is None:
            return
        # clear console
        self.textField.clear()
        # setup ssh session if remote mode is ON
        if self.remoteMode:
            ssh = SshSession(self.sshIp, self.sshUser, self.sshPasswd)
            ssh.initialize()
        else:
            ssh = None
        # get data and maximum length of entry for better output
        data, maximum = smart_parser(selected_drive, ssh)
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

    def set_remote_mode(self):
        if self.localRadioBtn.isChecked():
            self.remoteMode = False
        elif self.sshRadioBtn.isChecked():
            self.remoteMode = True
        self.refresh()

    def refresh(self):
        self.sshIp = self.sshIpInput.text()
        self.sshUser = self.sshUserInput.text()
        self.sshPasswd = self.sshPasswdInput.text()
        self.setup()

    def restore(self):
        self.sshIpInput.setText(self.sshIp)
        self.sshUserInput.setText(self.sshUser)
        self.sshPasswdInput.setText(self.sshPasswd)

    def default(self):
        self.localRadioBtn.setChecked(True)
        self.sshIpInput.clear()
        self.sshUserInput.clear()
        self.sshPasswdInput.clear()
        self.settings.clear()

    def update_queue(self, drive, mode):
        self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        for idx, entry in enumerate(QUEUE_TABLE):
            label = QtWidgets.QLabel()
            if entry == "ID":                   # ID
                t = datetime.datetime.now()
                t = t.strftime("%d%m%y-%H%M%S")
                label.setText(t)
            if entry == "Process":              # PROCESS
                if mode == 'erase':
                    label.setText("Erase")
                elif mode == 'smart':
                    label.setText("Smart check")
                elif mode == 'cannolo':
                    label.setText("Cannolo")
            if entry == "Disk":                 # DISK
                label.setText(drive)
            if entry == "Status":               # STATUS
                if self.queueTable.rowCount() != 1:
                    label.setPixmap(QtGui.QPixmap(PATH["PENDING"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
                else:
                    label.setPixmap(QtGui.QPixmap(PATH["PROGRESS"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
            if entry == "Progress":             # PROGRESS
                label = QtWidgets.QProgressBar()
                label.setValue(50)

            label.setAlignment(Qt.AlignCenter)
            self.queueTable.setCellWidget(self.queueTable.rowCount() - 1, idx, label)

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

    def save_ip(self):
        ip = self.sshIpInput.text()
        self.ipList.addItem(ip)

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("conf/remoteMode", str(self.remoteMode))
        self.settings.setValue("conf/sshIp", self.sshIpInput.text())
        self.settings.setValue("conf/sshUser", self.sshUserInput.text())
        self.settings.setValue("conf/sshPasswd", self.sshPasswdInput.text())
        print(self.settings.value("conf/remoteMode"))

class SshSession:
    def __init__(self, ip, user, passwd):
        self.ip = ip
        self.user = user
        self.passwd = passwd
        self.session = paramiko.SSHClient()

    def initialize(self):
        self.session.load_system_host_keys()
        try:
            self.session.connect(self.ip, username=self.user, password=self.passwd)
            return True
        except paramiko.ssh_exception.AuthenticationException:
            message = "Authentication failed.\nCheck user and password."
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, ".Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False
        except socket.gaierror:
            message = "Cannot find ip address.\nCheck if you have inserted a wrong ip."
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False
        except paramiko.ssh_exception.NoValidConnectionsError:
            message = "Cannot find ip address.\nCheck if you have inserted a wrong ip."
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False
        except:
            message = sys.exc_info()
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False

    def kill(self):
        self.session.close()

    def execute(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        output = []
        for line in stdout:
            output.append(line.rstrip('\n'))
        return output


def smart_parser(drive: str, ssh):
    output = ssh.execute('sudo smartctl -a /dev/' + drive)
    attributes = []
    for line in output:
        attributes.append(line)

    results = []
    fase = ""
    MAX = 0

    for attr in attributes:
        if attr == "=== START OF INFORMATION SECTION ===":
            fase = "INFO"
        elif attr == "=== START OF READ SMART DATA SECTION ===":
            fase = "SMART"
        if any(req for req in REQUIREMENTS if req in attr):
            if fase == "INFO":
                asd = attr.split(":")
                results.append([asd[0] , asd[1].lstrip()])
                if len(attr.split(":")[0]) > MAX:
                    MAX = len(attr.split(":")[0])
            elif fase == "SMART":
                splitted = attr.split()
                results.append([splitted[1] , splitted[8], splitted[9]])
                if len(splitted[1]) > MAX:
                    MAX = len(splitted[1])
    
    return results, MAX


def smart_analyzer(data, text):
    check = ''
    for attribute in data:
        if attribute[0] == "Power_On_Hours":
            value = normalizer(attribute[2])
            if int(value) > 10000:
                check = "OLD"
            else:
                check = "OK"
        
        if len(attribute) == 3:
            if attribute[1].lstrip() != "-":
                check = "FAIL"
        
        if attribute[0] == "Current Pending Sector Count":
            value = normalizer(attribute[2])
            if int(value) > 0:
                check = "FAIL"
        
        if attribute[0] == "Reallocated_Sector_Ct":
            value = normalizer(attribute[2])
            if int(value) > 0:
                check = "FAIL"
                
        
    if check == "OK":
        text.append("SMART DATA CHECK  --->  OK")
    elif check == "OLD":
        text.append("SMART DATA CHECK  --->  OLD")
    elif check == "FAIL":
        text.append("SMART DATA CHECK  --->  FAIL\nHowever, check if the disc is functional")
    
    text.append("\nIl risultato è indicativo, non gettare l'hard disk se il check è FAIL")
    return text

def get_disks(ssh):
    output = ssh.execute('lsblk -d')
    result = []
    for line in output:
        if line[0] == 's':
            temp = " ".join(line.split())
            temp = temp.split(" ")
            result.append([temp[0], temp[3]])
    return result

def local_setup(system):
    if system == 'win32':
        label = []
        size = []
        drive = []
        for line in subprocess.getoutput("wmic logicaldisk get caption").splitlines():
            if line.rstrip() != 'Caption' and line.rstrip() != '':
                label.append(line.rstrip())
        for line in subprocess.getoutput("wmic logicaldisk get size").splitlines():
            if line.rstrip() != 'Size' and line.rstrip() != '':
                size.append(line)
        for idx, line in enumerate(size):
            drive += [[label[idx],line]]
        return drive

    else:
        pass

def win_path(linuxPath):
    winPath = r""
    for char in linuxPath:
        if char == '/':
            winPath += '\\'
        else:
            winPath += char
    return winPath

if __name__ == "__main__":
    main()
