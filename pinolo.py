#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
from client import *
from utilites import *
from typing import Union
import sys
import traceback
from multiprocessing import Process

PATH = {"REQUIREMENTS": "/requirements_client.txt",

        "UI": "/assets/qt/interface.ui",
        "INFOUI": "/assets/qt/info.ui",
        "CANNOLOUI": "/assets/qt/cannolo_select.ui",

        "ICON": "/assets/icon.png",

        "VAPORWAVE_AUDIO": "/assets/vaporwave_theme.mp3",

        "ASD": "/assets/asd/asd.gif",
        "ASDVAP": "/assets/asd/asdvap.gif",

        "RELOAD": "/assets/reload/reload.png",
        "WHITERELOAD": "/assets/reload/reload_white.png",
        "VAPORWAVERELOAD": "/assets/reload/vapman.png",

        "PENDING": "/assets/table/pending.png",
        "PROGRESS": "/assets/table/progress.png",
        "OK": "/assets/table/ok.png",
        "WARNING": "/assets/table/warning.png",
        "ERROR": "/assets/table/error.png",
        "STOP": "/assets/stop.png",

        "WEEETXT": "/assets/weee_text.png",

        "SERVER": "/basilico.py",

        "DEFAULTTHEME": "/themes/defaultTheme.ssh",
        "DARKTHEME": "/themes/darkTheme.ssh",
        "VAPORTHEME": "/themes/vaporwaveTheme.ssh",
        "ASDTHEME": "/themes/asdTheme.ssh",
        "WEEETHEME": "/themes/weeeTheme.ssh",
        "VAPORWINTHEME": "/themes/vaporwaveWinTheme.ssh",
        "ASDWINTHEME": "/themes/asdWinTheme.ssh",
        "WEEEWINTHEME": "/themes/weeeWinTheme.ssh"}

QUEUE_TABLE = ["ID",
               "Process",
               "Disk",
               "Status",
               "Progress"
               ]

CURRENT_PLATFORM = sys.platform

initialize_path(CURRENT_PLATFORM, PATH)

try:
    from PyQt5 import uic
    from PyQt5.QtGui import QIcon, QMovie
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QTableWidgetItem
    import playsound
except ModuleNotFoundError:
    check_requirements(PATH["REQUIREMENTS"])
    from PyQt5 import uic
    from PyQt5.QtGui import QIcon, QMovie
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QTableWidgetItem
    import playsound

# UI class
class Ui(QtWidgets.QMainWindow):
    def __init__(self, app: QtWidgets.QApplication) -> None:
        super(Ui, self).__init__()
        uic.loadUi(PATH["UI"], self)
        self.app = app
        self.host = "127.0.0.1"
        self.port = 1030
        self.remoteMode = False
        self.client: ReactorThread
        self.client = None
        self.manual_cannolo = False
        self.selected_drive = None
        self.settings = QtCore.QSettings("WEEE-Open", "PESTO")
        self.audio_process = Process(target=playsound.playsound, args=('assets/vaporwave_theme.mp3',))

        """ Defining all items in GUI """
        self.globalTab = self.findChild(QtWidgets.QTabWidget, 'globalTab')
        self.gif = QMovie(PATH["ASD"])
        self.diskTable = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.queueTable = self.findChild(QtWidgets.QTableWidget, 'queueTable')
        self.reloadButton = self.findChild(QtWidgets.QPushButton, 'reloadButton')
        self.eraseButton = self.findChild(QtWidgets.QPushButton, 'eraseButton')
        self.smartButton = self.findChild(QtWidgets.QPushButton, 'smartButton')
        self.cannoloButton = self.findChild(QtWidgets.QPushButton, 'cannoloButton')
        self.taralloButton = self.findChild(QtWidgets.QPushButton, 'taralloButton')
        self.stdProcedureButton = self.findChild(QtWidgets.QPushButton, 'stdProcButton')
        self.localRadioBtn = self.findChild(QtWidgets.QRadioButton, 'localRadioBtn')
        self.remoteRadioBtn = self.findChild(QtWidgets.QRadioButton, 'remoteRadioBtn')
        self.hostInput = self.findChild(QtWidgets.QLineEdit, 'remoteIp')
        self.portInput = self.findChild(QtWidgets.QLineEdit, 'remotePort')
        self.restoreButton = self.findChild(QtWidgets.QPushButton, "restoreButton")
        self.defaultButton = self.findChild(QtWidgets.QPushButton, "defaultButton")
        self.saveButton = self.findChild(QtWidgets.QPushButton, "saveButton")
        self.ipList = self.findChild(QtWidgets.QListWidget, "ipList")
        self.findButton = self.findChild(QtWidgets.QPushButton, "findButton")
        self.cannoloLabel = self.findChild(QtWidgets.QLabel, "cannoloLabel")
        self.themeSelector = self.findChild(QtWidgets.QComboBox, 'themeSelector')
        self.directoryText = self.findChild(QtWidgets.QLineEdit, "directoryText")
        self.smartLayout = self.findChild(QtWidgets.QVBoxLayout, 'smartLayout')
        self.smartTabs = SmartTabs()
        self.smartLayout.addWidget(self.smartTabs)
        self.stop_action = QtWidgets.QAction("Stop", self)
        self.remove_action = QtWidgets.QAction("Remove", self)
        self.remove_all_action = QtWidgets.QAction("Remove All", self)
        self.info_action = QtWidgets.QAction("Info", self)
        self.asdlabel = self.findChild(QtWidgets.QLabel, 'asdLabel')
        self.asdGif = QMovie(PATH["ASD"])
        self.asdGif.setScaledSize(QtCore.QSize().scaled(self.asdlabel.width(), self.asdlabel.height(),
                                                        Qt.KeepAspectRatio))
        self.asdGif.start()
        self.asdlabel.setMovie(self.asdGif)

        """ Initialization operations """
        self.set_items_functions()
        self.localServer = LocalServer()
        self.localServer.update.connect(self.server_com)
        if CURRENT_PLATFORM == 'win32':
            if self.settings.value("win32ServerStartupDialog") != 1:
                message = "Cannot run local server on windows machine."
                if critical_dialog(message=message, dialog_type='ok_dna'):
                    self.settings.setValue("win32ServerStartupDialog", 1)
            self.app.setStyle("Windows")
        self.show()
        self.setup()

    def on_table_select(self, selected):
        sel = selected.count()
        if sel == 0:
            self.stop_action.setEnabled(False)
            self.remove_action.setEnabled(False)
            self.info_action.setEnabled(False)
        else:
            self.stop_action.setEnabled(True)
            self.remove_action.setEnabled(True)
            self.info_action.setEnabled(True)

    def set_items_functions(self):
        # set icon
        self.setWindowIcon(QIcon(PATH["ICON"]))

        # get latest configuration
        self.latest_conf()

        # disks table
        self.diskTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.diskTable.horizontalHeader().setStretchLastSection(True)
        self.diskTable.setColumnWidth(0, 65)
        self.diskTable.setColumnWidth(1, 65)
        self.diskTable.setColumnWidth(2, 65)
        self.diskTable.horizontalHeader().setStretchLastSection(True)
        self.diskTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        # queue table
        self.queueTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.queueTable.setRowCount(0)
        self.queueTable.horizontalHeader().setStretchLastSection(True)
        self.queueTable.setColumnWidth(0, 125)
        self.queueTable.setColumnWidth(2, 65)
        self.queueTable.setColumnWidth(3, 65)
        self.queueTable.setColumnWidth(4, 50)
        self.queueTable.horizontalHeader().setStretchLastSection(True)
        self.queueTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.queueTable.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.stop_action.triggered.connect(self.queue_stop)
        self.queueTable.addAction(self.stop_action)
        self.stop_action.setEnabled(False)
        self.remove_action.triggered.connect(self.queue_remove)
        self.queueTable.addAction(self.remove_action)
        self.remove_action.setEnabled(False)
        self.remove_all_action.triggered.connect(self.queue_clear)
        self.queueTable.addAction(self.remove_all_action)
        self.remove_all_action.setEnabled(True)
        self.info_action.triggered.connect(self.queue_info)
        self.queueTable.addAction(self.info_action)
        self.info_action.setEnabled(False)
        self.queueTable.selectionModel().selectionChanged.connect(self.on_table_select)

        # reload button
        self.reloadButton.clicked.connect(self.refresh)
        self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))

        # erase button
        self.eraseButton.clicked.connect(self.erase)

        # smart button
        self.smartButton.clicked.connect(self.smart)

        # cannolo button
        self.cannoloButton.clicked.connect(self.cannolo)

        # standard procedure button
        self.stdProcedureButton.clicked.connect(self.std_procedure)

        # tarallo button
        self.taralloButton.clicked.connect(self.load_to_tarallo)

        # text field
        # self.textField.setReadOnly(True)
        # font = self.textField.document().defaultFont()
        # font.setFamily("Monospace")
        # font.setStyleHint(QtGui.QFont.Monospace)
        # self.textField.document().setDefaultFont(font)
        # self.textField.setCurrentFont(font)
        # self.textField.setFontPointSize(10)

        # local radio button
        if not self.remoteMode:
            self.localRadioBtn.setChecked(True)
        self.localRadioBtn.clicked.connect(self.set_remote_mode)

        # remote radio button
        if self.remoteMode:
            self.remoteRadioBtn.setChecked(True)
        self.remoteRadioBtn.clicked.connect(self.set_remote_mode)

        # host input
        self.hostInput.setText(self.host)

        # port input
        if self.port is not None:
            self.portInput.setText(str(self.port))

        # restore button
        self.restoreButton.clicked.connect(self.restore)

        # default values button
        self.defaultButton.clicked.connect(self.default_config)

        # remove config button
        self.defaultButton = self.findChild(QtWidgets.QPushButton, "removeButton")
        self.defaultButton.clicked.connect(self.remove_config)

        # save config button
        self.saveButton.clicked.connect(self.save_config)

        # configuration list
        for key in self.settings.childKeys():
            if "saved" in key:
                values = self.settings.value(key)
                self.ipList.addItem(values[0])
        self.ipList.clicked.connect(self.load_config)

        # find button
        self.findButton.clicked.connect(self.find_image)

        # directory text
        for key in self.settings.childKeys():
            if "cannoloDir" in key:
                self.directoryText.setText(str(self.settings.value(key)))
        if self.remoteMode:
            self.directoryText.setReadOnly(False)

        # cannolo label
        if self.remoteMode:
            self.cannoloLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")
        else:
            self.cannoloLabel.setText("")

        # theme selector
        for key in self.settings.childKeys():
            if "theme" in key:
                self.themeSelector.setCurrentText(self.settings.value(key))
                self.set_theme()
        self.themeSelector.currentTextChanged.connect(self.set_theme)

    def latest_conf(self):
        self.remoteMode = self.settings.value("remoteMode")
        if self.remoteMode == 'False':
            self.remoteMode = False
            self.host = "127.0.0.1"
            self.port = 1030
        else:
            self.remoteMode = True
            try:
                self.host = self.settings.value("remoteIp")
                self.port = int(self.settings.value("remotePort"))
            except ValueError:
                if self.host is None:
                    self.host = "127.0.0.1"
                self.port = 1030
            except TypeError:
                if self.host is None:
                    self.host = "127.0.0.1"
                self.port = 1030

    def setup(self):
        self.set_remote_mode()

        # check if the host and port field are set
        if self.host is None and self.port is None:
            message = "The host and port combination is not set.\nPlease visit the settings section."
            warning_dialog(message, dialog_type='ok')

        """
        The client try to connect to the BASILICO. If it can't and the client is in remote mode, then 
        a critical error is shown and the client goes in idle. If the client is in local mode and it cannot reach a
        BASILICO server, a new BASILICO process is instantiated.
        """
        self.client = ReactorThread(self.host, self.port, self.remoteMode)
        self.client.updateEvent.connect(self.gui_update)
        self.client.start()

    def deselect(self):
        self.queueTable.clearSelection()
        self.queueTable.clearFocus()

    def queue_stop(self):
        pid = self.queueTable.item(self.queueTable.currentRow(), 0).text()
        message = 'Do you want to stop the process?\nID: ' + pid
        if warning_dialog(message, dialog_type='yes_no') == QtWidgets.QMessageBox.Yes:
            self.client.send(f"stop {pid}")
        self.deselect()

    def queue_remove(self):
        pid = self.queueTable.item(self.queueTable.currentRow(), 0).text()
        message = 'With this action you will also stop the process (ID: ' + pid + ")\n"
        message += 'Do you want to proceed?'
        if warning_dialog(message, dialog_type='yes_no') == QtWidgets.QMessageBox.Yes:
            self.client.send(f"remove {pid}")
            self.queueTable.removeRow(self.queueTable.currentRow())
        self.deselect()

    def queue_clear(self):
        self.queueTable.setRowCount(0)
        self.client.send("remove_all")

    def queue_info(self):
        process = self.queueTable.item(self.queueTable.currentRow(), 1).text()
        message = ''
        if process == "Smart check":
            message += "Process type: " + process + "\n"
            message += "Get SMART data from the selected drive\n"
            message += "and print the output to the console."
        elif process == "Erase":
            message += "Process type: " + process + "\n"
            message += "Wipe off all data in the selected drive."
        info_dialog(message)
        self.deselect()

    def std_procedure(self):
        message = "Do you want to wipe all disk's data and load a fresh system image?"
        dialog = warning_dialog(message, dialog_type='yes_no_chk')
        if dialog[0] == QtWidgets.QMessageBox.Yes:
            self.load_to_tarallo(std=True)
            self.erase(std=True)
            self.smart(std=True)
            if dialog[1]:
                self.cannolo(std=True)
            self.sleep()

    def erase(self, std=False):
        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                message = "There are no selected drives."
                warning_dialog(message, dialog_type='ok')
                return
            else:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            if not std:
                message = "Do you want to wipe all disk's data?\nDisk: " + self.selected_drive
                if critical_dialog(message, dialog_type='yes_no') != QtWidgets.QMessageBox.Yes:
                    return
            self.client.send("queued_badblocks " + self.selected_drive)

        except BaseException:
            print("GUI: Error in erase Function")

    def smart(self, std=False):
        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type='ok')
                    return
                return
            # TODO: Add new tab for every smart requested. If drive tab exist, use it.
            drive = self.selected_drive.text().lstrip("Disk ")
            self.client.send("queued_smartctl " + drive)

        except BaseException:
            print("GUI: Error in smart function.")

    def cannolo(self, std=False):
        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            directory = self.directoryText.text().rsplit("/", 1)[0] + '/'
            if self.selected_drive is None:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type='ok')
                    return
                return
            else:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            if not std:
                message = "Do you want to load a fresh system installation in disk " + self.selected_drive + "?"
                if warning_dialog(message, dialog_type='yes_no') != QtWidgets.QMessageBox.Yes:
                    return
                self.client.send(f"list_iso {directory}")
                self.manual_cannolo = True
                return
            self.client.send(f"queued_cannolo {self.selected_drive}")

        except BaseException:
            print("GUI: Error in cannolo function.")

    def load_to_tarallo(self, std=False):
        self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
        selected_drive_id = self.diskTable.item(self.diskTable.currentRow(), 1).text()
        if selected_drive_id != '':
            message = "The selected disk have alredy a TARALLO id."
            warning_dialog(message, dialog_type='ok')
            return
        if not std:
            message = "Do you want to load the disk informations into TARALLO?"
            if warning_dialog(message, dialog_type='yes_no') == QtWidgets.QMessageBox.No:
                return
        self.selected_drive = self.selected_drive.text().lstrip("Disk ")
        self.client.send(f"queued_upload_to_tarallo {self.selected_drive}")

    def sleep(self, std=False):
        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type='ok')
                    return
                return
            else:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            self.client.send("queued_sleep " + self.selected_drive)

        except BaseException:
            print("GUI: Error in cannolo function.")

    def set_remote_mode(self):
        # if CURRENT_PLATFORM == 'win32':
        #     self.remoteRadioBtn.setChecked(True)
        #     self.localRadioBtn.setCheckable(False)
        if self.localRadioBtn.isChecked():
            if not self.remoteMode:
                self.client.send("close_at_end")
            self.remoteMode = False
            self.settings.setValue("latestHost", self.host)
            self.settings.setValue("latestPort", self.port)
            self.host = "127.0.0.1"
            self.port = 1030
            self.hostInput.setText(self.host)
            self.portInput.setText(str(self.port))
            self.hostInput.setReadOnly(True)
            self.portInput.setReadOnly(True)
            self.saveButton.setEnabled(False)
            self.directoryText.setReadOnly(True)
            self.cannoloLabel.setText("")
        elif self.remoteRadioBtn.isChecked():
            if not self.remoteMode:
                self.host = self.settings.value("latestHost")
                self.port = int(self.settings.value("latestPort"))
                self.client.send("close_at_end")
            self.remoteMode = True
            self.hostInput.setReadOnly(False)
            self.hostInput.setText(self.host)
            self.portInput.setReadOnly(False)
            self.portInput.setText(str(self.port))
            self.saveButton.setEnabled(True)
            self.directoryText.setReadOnly(False)
            self.cannoloLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")

    def refresh(self):
        self.host = self.hostInput.text()
        self.port = int(self.portInput.text())
        self.client.reconnect(self.host, self.port)

    def restore(self):
        self.hostInput.setText(self.host)
        self.portInput.setText(str(self.port))

    def update_queue(self, pid, drive, mode):
        # self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        row = self.queueTable.rowCount()
        self.queueTable.insertRow(row)
        for idx, entry in enumerate(QUEUE_TABLE):
            label: Union[None, str, QtWidgets.QLabel, QtWidgets.QProgressBar, QtWidgets.QTableWidgetItem]
            label = None
            if entry == "ID":  # ID
                label = pid
            elif entry == "Process":  # PROCESS
                if mode == 'queued_badblocks':
                    label = "Erase"
                elif mode == 'queued_smartctl' or mode == 'smartctl':
                    label = "Smart check"
                elif mode == 'queued_cannolo':
                    label = "Cannolo"
                else:
                    label = "Unknown"
            elif entry == "Disk":  # DISK
                label = drive
            elif entry == "Status":  # STATUS
                if self.queueTable.rowCount() != 0:
                    label = QtWidgets.QLabel()
                    label: QtWidgets.QLabel
                    label.setPixmap(QtGui.QPixmap(PATH["PENDING"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
                else:
                    label: QtWidgets.QLabel
                    label.setPixmap(QtGui.QPixmap(PATH["PROGRESS"]).scaled(25, 25, QtCore.Qt.KeepAspectRatio))
            elif entry == "Progress":  # PROGRESS
                label = QtWidgets.QProgressBar()
                label.setValue(0)

            if entry in ["ID", "Process", "Disk"]:
                label = QTableWidgetItem(label)
                label: QtWidgets.QTableWidgetItem
                label.setTextAlignment(Qt.AlignCenter)
                self.queueTable.setItem(row, idx, label)
            elif entry == "Status":
                label.setAlignment(Qt.AlignCenter)
                self.queueTable.setCellWidget(row, idx, label)
            else:
                label.setAlignment(Qt.AlignCenter)
                layout = QtWidgets.QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(label)
                widget = QtWidgets.QWidget()
                widget.setLayout(layout)
                self.queueTable.setCellWidget(row, idx, widget)

    def save_config(self):
        ip = self.hostInput.text()
        port = self.portInput.text()
        if self.ipList.findItems(ip, Qt.MatchExactly):
            message = "Do you want to overwrite the old configuration?"
            if warning_dialog(message, dialog_type='yes_no') == QtWidgets.QMessageBox.Yes:
                self.settings.setValue("saved-" + ip, [ip, port])
        else:
            self.ipList.addItem(ip)
            self.settings.setValue("saved-" + ip, [ip, port])

    def remove_config(self):
        ip = self.ipList.currentItem().text()
        message = "Do you want to remove the selected configuration?"
        if warning_dialog(message, dialog_type='yes_no') == QtWidgets.QMessageBox.Yes:
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
        if critical_dialog(message, dialog_type="yes_no") == QtWidgets.QMessageBox.Yes:
            self.settings.clear()
            self.ipList.clear()
            self.setup()

    def find_image(self):
        # noinspection PyBroadException
        try:
            if self.remoteMode:
                directory = self.directoryText.text()
                splitted_dir = directory.rsplit("/", 1)
                if len(splitted_dir[1].split(".")) > 1:
                    self.client.send("list_iso " + directory.rsplit("/", 1)[0])
                else:
                    if directory[-1] != '/':
                        directory += '/'
                    self.client.send("list_iso " + directory)
            else:
                dialog = QtWidgets.QFileDialog()
                directory = dialog.getExistingDirectory(self, "Open Directory", "/home",
                                                        QtWidgets.QFileDialog.ShowDirsOnly)
                self.directoryText.setText(directory)
                
        except BaseException as ex:
            print(f"GUI: Error in smart function [{ex}]")

    def set_default_cannolo(self, directory: str, img: str):
        if self.set_default_cannolo:
            self.directoryectoryText.setText(directory)
            self.statusBar().showMessage(f"Default cannolo image set as {img}.iso")

    def use_cannolo_img(self, directory: str, img: str):
        self.statusBar().showMessage(f"Sending cannolo to {self.selected_drive} with {img}")
        self.client.send(f"queued_cannolo {self.selected_drive}")

    def set_theme(self):
        theme = self.themeSelector.currentText()
        if theme == "Vaporwave":
            try:
                f = open('assets/vaporwave_theme.mp3')
                f.close()
                self.audio_process = Process(target=playsound.playsound, args=('assets/vaporwave_theme.mp3',))
                self.audio_process.start()
            except IOError:
                self.statusBar().showMessage("assets/vaporwave_theme.mp3 not found.")
        else:
            try:
                self.audio_process.terminate()
            except:
                print("No audio")
        if theme == "Dark":
            with open(PATH["DARKTHEME"], "r") as file:
                self.app.setStyleSheet(file.read())
            self.reloadButton.setIcon(QIcon(PATH["WHITERELOAD"]))
            self.backgroundLabel.clear()
            self.reloadButton.setIconSize(QtCore.QSize(25,25))
            self.asd_gif_set(PATH["ASD"])
            self.cannoloLabel.setStyleSheet('color: yellow')
        elif theme == "Vaporwave":
            if CURRENT_PLATFORM == 'win32':
                with open(PATH["VAPORWINTHEME"]) as file:
                    self.app.setStyleSheet(file.read())
            else:
                with open(PATH["VAPORTHEME"], "r") as file:
                    self.app.setStyleSheet(file.read())
            self.reloadButton.setIcon(QIcon(PATH["VAPORWAVERELOAD"]))
            self.reloadButton.setIconSize(QtCore.QSize(50,50))
            self.backgroundLabel.clear()
            self.asd_gif_set(PATH["ASDVAP"])
            self.cannoloLabel.setStyleSheet('color: rgb(252, 186, 3)')
        elif theme == "Asd":
            if CURRENT_PLATFORM == 'win32':
                with open(PATH["ASDWINTHEME"]) as file:
                    self.app.setStyleSheet(file.read())
            else:
                with open(PATH["ASDTHEME"], "r") as file:
                    self.app.setStyleSheet(file.read())
            self.backgroundLabel = self.findChild(QtWidgets.QLabel, "backgroundLabel")
            self.movie = QMovie(PATH["ASD"])
            self.movie.setScaledSize(QtCore.QSize().scaled(400, 400, Qt.KeepAspectRatio))
            self.movie.start()
            self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))
            self.backgroundLabel.setMovie(self.movie)
            self.reloadButton.setIconSize(QtCore.QSize(25,25))
            self.asd_gif_set(PATH["ASD"])
            self.cannoloLabel.setStyleSheet('color: blue')
        elif theme == "WeeeOpen":
            if CURRENT_PLATFORM == 'win32':
                with open(PATH["WEEEWINTHEME"]) as file:
                    self.app.setStyleSheet(file.read())
            self.backgroundLabel.clear()
            self.backgroundLabel.setPixmap(QtGui.QPixmap(PATH["WEEETXT"]))
            self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))
            self.reloadButton.setIconSize(QtCore.QSize(25, 25))
            self.asd_gif_set(PATH["ASD"])
        elif theme == "Default":
            self.app.setStyleSheet("")
            with open(PATH["DEFAULTTHEME"], "r") as file:
                self.app.setStyleSheet(file.read())
            self.backgroundLabel.clear()
            self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))
            self.reloadButton.setIconSize(QtCore.QSize(25,25))
            self.asd_gif_set(PATH["ASD"])
            self.cannoloLabel.setStyleSheet('color: blue')
        self.smartTabs.set_style(theme)

    def asd_gif_set(self, dir: str):
        self.asdGif = QMovie(dir)
        self.asdGif.setScaledSize(
            QtCore.QSize().scaled(self.asdlabel.width(), self.asdlabel.height(), Qt.KeepAspectRatio))
        self.asdGif.start()
        self.asdlabel.setMovie(self.asdGif)

    def server_com(self, cmd: str, st2: str):
        if cmd == 'SERVER_READY':
            print("GUI: Local server loaded. Connecting...")
            self.client.reconnect(self.host, self.port)
        elif cmd == 'SERVER_ALREADY_UP':
            print("GUI: Local server already up. Reconnecting...")
            self.client.reconnect(self.host, self.port)

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
            params: Union[dict, list]
        except json.decoder.JSONDecodeError:
            print(f"GUI: Ignored exception while parsing {cmd}, expected JSON but this isn't: {params}")

        if cmd == 'queue_status' or cmd == 'get_queue':
            if cmd == 'queue_status':
                params = [params]
            for param in params:
                param: dict
                row = 0
                rows = self.queueTable.rowCount()
                for row in range(rows + 1):
                    # Check if we already have that id
                    item = self.queueTable.item(row, 0)
                    if item is not None and item.text() == param["id"]:
                        break
                    elif item is None:
                        self.update_queue(pid=param["id"], drive=param["target"], mode=param["command"])
                        rows += 1
                progress_bar = self.queueTable.cellWidget(row, 4).findChild(QtWidgets.QProgressBar)
                status_cell = self.queueTable.cellWidget(row, 3)
                progress_bar.setValue(int(param["percentage"]))
                if param["stale"]:
                    pass
                elif param["stopped"]:
                    # TODO: we don't have an icon for this, maybe we should
                    status_cell.setPixmap(QtGui.QPixmap(PATH["STOP"]).scaledToHeight(25, Qt.SmoothTransformation))
                elif param["error"]:
                    status_cell.setPixmap(QtGui.QPixmap(PATH["ERROR"]).scaledToHeight(25, Qt.SmoothTransformation))
                elif param["finished"]:  # and not error
                    status_cell.setPixmap(QtGui.QPixmap(PATH["OK"]).scaledToHeight(25, Qt.SmoothTransformation))
                elif param["started"]:
                    status_cell.setPixmap(QtGui.QPixmap(PATH["PROGRESS"]).scaledToHeight(25, Qt.SmoothTransformation))
                else:
                    status_cell.setPixmap(QtGui.QPixmap(PATH["PENDING"]).scaledToHeight(25, Qt.SmoothTransformation))

        elif cmd == 'get_disks':
            drives = params
            if len(drives) <= 0:
                self.diskTable.setRowCount(0)
                return
            # compile disks table with disks list
            rows = 0
            for d in drives:
                d: dict
                if "[BOOT]" in d["mountpoint"]:
                    continue
                rows += 1
                self.diskTable.setRowCount(rows)
                if sys.platform == 'win32':
                    self.diskTable.setItem(rows - 1, 0, QTableWidgetItem("Disk " + d["path"]))
                else:
                    self.diskTable.setItem(rows - 1, 0, QTableWidgetItem(d["path"]))
                self.diskTable.setItem(rows - 1, 1, QTableWidgetItem(d["code"]))
                self.diskTable.setItem(rows - 1, 2, QTableWidgetItem(str(int(int(d["size"]) / 1000000000)) + " GB"))

        elif cmd == 'smartctl' or cmd == 'queued_smartctl':
            text = ("Smartctl output:\n " + params["output"]).splitlines()
            tab_count = self.smartTabs.count()
            tab = 0
            for tab in range(tab_count + 1):
                if self.smartTabs.tabText(tab) == params["disk"]:
                    message= "Il tab per il dosco esiste già asd.\nVuoi sovrascrivere l'output?"
                    if warning_dialog(message, dialog_type="yes_no") == QtWidgets.QMessageBox.Yes:
                        for line in text:
                            self.smartTabs.text_boxes[tab].append(line)
                elif tab == tab_count:
                        self.smartTabs.add_tab(params["disk"], params["status"], params["updated"], text)

        elif cmd == 'connection_failed':
            message = params["reason"]
            if not self.remoteMode:
                print("GUI: Connection Failed: Local server not running.")
                print("GUI: Trying to start local server...")
                self.localServer.start()
                return
            if "Connection was refused by other side" in message:
                message = "Cannot find BASILICO server.\nCheck if it's running in the " \
                          "targeted machine."
            warning_dialog(message, dialog_type="ok")

        elif cmd == 'connection_made':
            self.statusBar().showMessage(f"Connected to {params['host']}:{params['port']}")

        # This is an example, the iso_list cmd does not exist now on server
        elif cmd == 'list_iso':
            self.dialog = CannoloDialog(PATH, params)
            if self.manual_cannolo:
                self.dialog.update.connect(self.use_cannolo_img)
                self.manual_cannolo = False
            else:
                self.dialog.update.connect(self.set_default_cannolo)

        elif cmd == 'error':
            message = params["message"]
            critical_dialog(message, dialog_type='ok')

        elif cmd == 'error_that_can_be_manually_fixed':
            message = params["message"]
            warning_dialog(message, dialog_type='ok')

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.settings.setValue("remoteMode", str(self.remoteMode))
        self.settings.setValue("remoteIp", self.hostInput.text())
        self.settings.setValue("remotePort", self.portInput.text())
        self.settings.setValue("cannoloDir", self.directoryText.text())
        self.settings.setValue("theme", self.themeSelector.currentText())
        self.client.stop(self.remoteMode)
        try:
            self.audio_process.terminate()
        except:
            print("No audio")


class LocalServer(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.server: subprocess.Popen
        self.server = None
        self.running = False

    def run(self):
        if not self.running:
            self.server = subprocess.Popen(["python", PATH["SERVER"]], stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
            while "Listening on" not in self.server.stderr.readline().decode('utf-8'):
                pass
            self.running = True
            self.update.emit("SERVER_READY", '')
        else:
            self.update.emit("SERVER_ALREADY_UP", '')

    def stop(self):
        if self.running:
            self.server.terminate()
        self.running = False


def main():
    # noinspection PyBroadException
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = Ui(app)
        app.exec_()

    except KeyboardInterrupt:
        print("KeyboardInterrupt")

    except BaseException:
        print(traceback.print_exc(file=sys.stdout))


if __name__ == "__main__":
    main()
