#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
import ctypes
import datetime
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QTableWidgetItem, QMenu
from utilites import *

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
        "ERROR": "/assets/error.png"}

QUEUE_TABLE = ["ID",
               "Process",
               "Disk",
               "Status",
               "Progress"
               ]

CURRENT_PLATFORM = sys.platform

if CURRENT_PLATFORM == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
    for path in PATH:
        PATH[path] = win_path(PATH[path])
else:
    for path in PATH:
        PATH[path] = linux_path(PATH[path])


def main():
    try:
        check_requirements(PATH["REQUIREMENTS"])
        app = QtWidgets.QApplication(sys.argv)
        window = Ui()
        app.exec_()

    except KeyboardInterrupt:
        print("KeyboardInterrupt")


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi(PATH["UI"], self)

        # set icon
        self.setWindowIcon(QIcon(PATH["ICON"]))

        # get latest configuration
        self.settings = QtCore.QSettings("WEEE-Open", "PESTO")
        self.remoteMode = self.settings.value("remoteMode")
        if self.remoteMode == 'False':
            self.remoteMode = False
        else:
            self.remoteMode = True
        self.remoteIp = self.settings.value("remoteIp")
        try:
            self.remotePort = int(self.settings.value("remotePort"))
        except ValueError:
            self.remotePort = None

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
        self.queueTable.setColumnWidth(3, 50)
        self.queueTable.horizontalHeader().setStretchLastSection(True)
        self.queueTable.installEventFilter(self)

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
        self.remoteIpInput = self.findChild(QtWidgets.QLineEdit, 'remoteIp')
        self.remoteIpInput.setText(self.remoteIp)

        # remotePort input
        self.remotePortInput = self.findChild(QtWidgets.QLineEdit, 'remotePort')
        if self.remotePort != None:
            self.remotePortInput.setText(str(self.remotePort))

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

        self.setup()
        self.show()

    def setup(self):
        # get remote drives list
        if self.remoteMode and self.remoteIp != None and self.remotePort != None:
            cmd = "get_disks_win"
            drives = UDP_client(cmd, ip=self.remoteIp, port=self.remotePort)
            drives = ast.literal_eval(drives)
        # gety local drives list
        else:
            drives = local_setup(sys.platform)

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

    def default_dialog(self):
        message = "Do you want to restore all settings to default?\nThis action is irrevocable."
        yes_no_dialog(message=message, yes_function=self.default, no_function=None)

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
        selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0).text()
        message = "Do you want to wipe all disk's data?\nDisk: " + selected_drive
        if critical_dialog(message, type='yes_no') != QtWidgets.QMessageBox.Yes:
            return
        self.textField.clear()
        if self.remoteMode:
            cmd = 'pialla ' + selected_drive
            data = UDP_client(cmd, ip=self.remoteIp, port=self.remotePort)
            self.textField.append(data)
            self.update_queue(drive=selected_drive, mode="erase")
        else:
            self.textField.append("Sto piallando il disco " + selected_drive)
            self.update_queue(drive=selected_drive, mode="erase")

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
        data, maximum = smart_parser(selected_drive, self.remoteMode, platform=CURRENT_PLATFORM,
                                     requirements=REQUIREMENTS)
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
            return
        self.textField.clear()
        if self.remoteMode:
            cmd = 'cannolo ' + selected_drive
            data = UDP_client(cmd, ip=self.remoteIp, port=self.remotePort)
            self.textField.append(data)
            self.update_queue(drive=selected_drive, mode="cannolo")
        else:
            self.textField.append("Sto cannolando il disco " + selected_drive)
            self.update_queue(drive=selected_drive, mode="cannolo")


    def set_remote_mode(self):
        if self.localRadioBtn.isChecked():
            self.remoteMode = False
            self.findButton.setEnabled(True)
            self.directoryText.setReadOnly(True)
            self.cannoloLabel.setText("")
        elif self.remoteRadioBtn.isChecked():
            self.remoteMode = True
            self.findButton.setEnabled(False)
            self.directoryText.setReadOnly(False)
            self.cannoloLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")

    def refresh(self):
        self.remoteIp = self.remoteIpInput.text()
        self.remotePort = int(self.remotePortInput.text())
        self.setup()

    def restore(self):
        self.remoteIpInput.setText(self.remoteIp)
        self.remotePortInput.setText(str(self.remotePort))

    def default(self):
        self.localRadioBtn.setChecked(True)
        self.remoteIpInput.clear()
        self.remotePortInput.clear()
        self.settings.clear()

    def update_queue(self, drive, mode):
        self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        for idx, entry in enumerate(QUEUE_TABLE):
            label = QtWidgets.QLabel()
            if entry == "ID":  # ID
                t = datetime.datetime.now()
                t = t.strftime("%d%m%y-%H%M%S")
                label.setText(t)
            if entry == "Process":  # PROCESS
                if mode == 'erase':
                    label.setText("Erase")
                elif mode == 'smart':
                    label.setText("Smart check")
                elif mode == 'cannolo':
                    label.setText("Cannolo")
            if entry == "Disk":  # DISK
                label.setText(drive)
            if entry == "Status":  # STATUS
                if self.queueTable.rowCount() != 1:
                    label.setPixmap(QtGui.QPixmap(PATH["PENDING"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
                else:
                    label.setPixmap(QtGui.QPixmap(PATH["PROGRESS"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
            if entry == "Progress":  # PROGRESS
                label = QtWidgets.QProgressBar()
                label.setValue(50)

            label.setAlignment(Qt.AlignCenter)
            self.queueTable.setCellWidget(self.queueTable.rowCount() - 1, idx, label)

    def save_config(self):
        ip = self.remoteIpInput.text()
        port = self.remotePortInput.text()
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
                self.remoteIpInput.setText(ip)
                self.remotePortInput.setText(port)

    def default_config(self):
        message = "Do you want to restore all settings to default?\nThis action is unrevocable."
        if critical_dialog(message, "yes_no") == QtWidgets.QMessageBox.Yes:
            self.settings.clear()
            self.ipList.clear()
            self.remoteIpInput.clear()
            self.remotePortInput.clear()

    def find_directory(self):
        dialog = QtWidgets.QFileDialog()
        dir = dialog.getExistingDirectory(self, "Open Directory", "/home", QtWidgets.QFileDialog.ShowDirsOnly)
        self.directoryText.setText(dir)

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("remoteMode", str(self.remoteMode))
        self.settings.setValue("remoteIp", self.remoteIpInput.text())
        self.settings.setValue("remotePort", self.remotePortInput.text())
        self.settings.setValue("cannoloDir", self.directoryText.text())


def smart_analyzer(data, text):
    check = ''
    for attribute in data:
        if attribute[0] == "Power_On_Hours":
            value = attribute[2]
            if int(value) > 10000:
                check = "OLD"
            else:
                check = "OK"
        
        if len(attribute) == 3:
            if attribute[1].lstrip() != "-":
                check = "FAIL"
        
        if attribute[0] == "Current Pending Sector Count":
            value = attribute[2]
            if int(value) > 0:
                check = "FAIL"
        
        if attribute[0] == "Reallocated_Sector_Ct":
            value = attribute[2]
            if int(value) > 0:
                check = "FAIL"

    if check == 'OK':
        text.append("SMART DATA CHECK  --->  OK")
    elif check == "OLD":
        text.append("SMART DATA CHECK  --->  OLD")
    elif check == "FAIL":
        text.append("SMART DATA CHECK  --->  FAIL\nHowever, check if the disc is functional")
    
    text.append("\nIl risultato è indicativo, non gettare l'hard disk se il check è FAIL")
    return text


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
            drive += [[label[idx], line]]
        return drive
    else:
        output = subprocess.getoutput('lsblk -d').splitlines()
        result = []
        for line in output:
            if line[0] == 's':
                temp = " ".join(line.split())
                temp = temp.split(" ")
                result.append([temp[0], temp[3]])
        return result


def yes_no_dialog(message, yes_function, no_function):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "Really suuuuuure?", message)
    dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
    dialog.addButton(QtWidgets.QMessageBox.No)
    dialog.setDefaultButton(QtWidgets.QMessageBox.No)
    pressed = dialog.exec_()
    if pressed == QtWidgets.QMessageBox.Yes:
        yes_function()
    else:
        if no_function is None:
            return
        no_function()

if __name__ == "__main__":
    main()
