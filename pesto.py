#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""

import subprocess
import os
import paramiko
import sys
import os
from PyQt5 import QtWidgets, uic, QtGui

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
        uic.loadUi(os.path.dirname(os.path.realpath(__file__)) + '/assets/interface.ui', self)

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
        self.execButton.setIcon(QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + '/assets/asdrow.png'))
        self.execButton.clicked.connect(self.execProgram)

        # text field
        self.textField = self.findChild(QtWidgets.QTextEdit, 'textEdit')
        self.textField.setReadOnly(True)
        self.textField.setCurrentFont(QtGui.QFont("Monospace"))
        self.textField.setFontPointSize(10)

        self.setup()
        self.show()

    def setup(self):
        # ssh session initialization
        ssh = SshSession(IP, USER, PASSWD)
        ssh.initialize()

        # get lsblk results
        drives = getDisks(ssh)

        for row, d in enumerate(drives):
            self.table.setRowCount(row+1)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(d[0]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(d[1]))

        ssh.kill()

    def execProgram(self):
        self.textField.clear()
        ssh = SshSession(IP, USER, PASSWD)
        ssh.initialize()
        if self.table.currentItem() is None:
            return
        idx = self.table.currentRow()
        drive = self.table.item(idx, 0).text()
        data, MAX = smartParser(drive, ssh)
        text = dataOutput(data, MAX)
        text.append("\n##########################\n")
        text = smartAnalizer(data, text)
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

class SshSession:
    def __init__(self, ip, user, passwd):
        self.ip = ip
        self.user = user
        self.passwd = passwd
        self.session = paramiko.SSHClient()

    def initialize(self):
        self.session.load_system_host_keys()
        self.session.connect(self.ip, username=self.user, password=self.passwd)

    def kill(self):
        self.session.close()

    def execute(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        output = []
        for line in stdout:
            output.append(line.rstrip('\n'))
        return output


def smartParser(drive: str, ssh):
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


def dataOutput(data, MAX):
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

def smartAnalizer(data, text):
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

def getDisks(ssh):
    output = ssh.execute('lsblk -d')
    result = []
    for line in output:
        if line[0] == 's':
            temp = " ".join(line.split())
            temp = temp.split(" ")
            result.append([temp[0], temp[3]])
    return result
# ---------------------------------------------------------------------


if __name__ == "__main__":
    main()
