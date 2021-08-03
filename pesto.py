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
import os
from PyQt5 import QtWidgets, uic, QtGui, QtCore

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

        # table view
        self.table = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem("Dischi"))
        self.table.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem("Dimensione"))
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setColumnWidth(0,77)
        self.table.setColumnWidth(1, 100)

        # exec button
        self.execButton = self.findChild(QtWidgets.QPushButton, 'execButton')
        if CURRENT_PLATFORM == 'win32':
            self.execButton.setIcon(QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + win_path(ARROW_PATH)))
        else:
            self.execButton.setIcon(QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + ARROW_PATH))
        self.execButton.clicked.connect(self.exec_program)

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


    def exec_program(self):
        self.textField.clear()
        ssh = SshSession(IP, USER, PASSWD)
        ssh.initialize()
        if self.table.currentItem() is None:
            return
        idx = self.table.currentRow()
        drive = self.table.item(idx, 0).text()
        data, max = smart_parser(drive, ssh)
        text = data_output(data, max)
        text.append("\n##########################\n")
        text = smart_analizer(data, text)
        for line in text:
            if "SMART DATA CHECK" in line:
                if "OLD" in line:
                    self.textField.setTextColor(QtGui.QColor("blue"))
                    self.textField.append(line)
                    self.textField.setTextColor(QtGui.QColor("black"))
                elif "FAIL" in line:
                    self.textField.setTextColor(QtGui.QColor("red"))
                    self.textField.append(line)
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


def data_output(data, MAX):
    output = []
    for row in data:
        temp = row[0]
        temp += ":"
        while len(temp) < MAX + SPACE:
            temp += " "
        if len(row) < 3:
            output.append(temp + row[1])
        else:
            output.append(temp + row[2])
    return output

def normalizer(rawValue):
    return(rawValue)

def smart_analizer(data, text):
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
