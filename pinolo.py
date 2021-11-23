#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""

from client import *
from utilites import *
from typing import Union
from multiprocessing import Process
from dotenv import load_dotenv
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem
import sys
import traceback
import playsound


PATH = {
    "REQUIREMENTS": "/requirements_client.txt",
    "ENV": "/.env",
    "UI": "/assets/qt/interface.ui",
    "UI_TEST": "/assets/qt/interface_test.ui",
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
    "WEEE": "/assets/backgrounds/weee_logo.png",
    "SERVER": "/basilico.py",
    "DEFAULTTHEME": "/themes/defaultTheme.css",
    "DARKTHEME": "/themes/darkTheme.css",
    "VAPORTHEME": "/themes/vaporwaveTheme.css",
    "ASDTHEME": "/themes/asdTheme.css",
    "WEEETHEME": "/themes/weeeTheme.css",
}

QUEUE_TABLE = ["ID", "Process", "Disk", "Status", "Progress"]

absolute_path(PATH)


# UI class
class Ui(QtWidgets.QMainWindow):
    def __init__(self, app: QtWidgets.QApplication) -> None:
        super(Ui, self).__init__()
        if os.getenv("TEST_MODE") == "1":
            uic.loadUi(PATH["UI_TEST"], self)
            self.testDiskTable = self.findChild(QtWidgets.QTableWidget, "testDiskTable")
            self.testDiskTable.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectRows
            )
            self.testDiskTable.horizontalHeader().setStretchLastSection(True)
            self.testDiskTable.setColumnWidth(0, 65)
            self.testDiskTable.setColumnWidth(1, 70)
            self.testDiskTable.setColumnWidth(2, 60)
            self.testDiskTable.horizontalHeader().setStretchLastSection(True)
            self.testDiskTable.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.Fixed
            )
            self.testDiskTable.cellClicked.connect(self.greyout_buttons)
            self.testRefreshBtn = self.findChild(
                QtWidgets.QPushButton, "testRefreshBtn"
            )
            self.testRefreshBtn.clicked.connect(self.refresh)
            self.testBadblocksBtn = self.findChild(
                QtWidgets.QPushButton, "testBadblocksBtn"
            )
            self.testBadblocksBtn.clicked.connect(self.test_badblocks)
            self.testSmartctlBtn = self.findChild(
                QtWidgets.QPushButton, "testSmartctlBtn"
            )
            self.testSmartctlBtn.clicked.connect(self.test_smartctl)
            self.testCannoloBtn = self.findChild(
                QtWidgets.QPushButton, "testCannoloBtn"
            )
            self.testCannoloBtn.clicked.connect(self.test_cannolo)
            self.testSleepBtn = self.findChild(QtWidgets.QPushButton, "testSleepBtn")
            self.testSleepBtn.clicked.connect(self.test_sleep)
            self.testStdProcBtn = self.findChild(
                QtWidgets.QPushButton, "testStdProcBtn"
            )
            self.testStdProcBtn.clicked.connect(self.test_std_proc)
            self.testStdProcNoCannoloBtn = self.findChild(
                QtWidgets.QPushButton, "testStdProcNoCannoloBtn"
            )
            self.testStdProcNoCannoloBtn.clicked.connect(self.test_std_proc_no_cannolo)
        else:
            uic.loadUi(PATH["UI"], self)
        self.app = app
        self.host = "127.0.0.1"
        self.port = 1030
        self.remoteMode = False
        self.client: ReactorThread
        self.client = None
        self.manual_cannolo = False
        self.selected_drive = None
        self.critical_mounts = []
        self.settings = QtCore.QSettings("WEEE-Open", "PESTO")
        self.audio_process = Process(
            target=playsound.playsound, args=("assets/vaporwave_theme.mp3",)
        )

        """ Defining all items in GUI """
        self.globalTab = self.findChild(QtWidgets.QTabWidget, "globalTab")
        self.gif = QMovie(PATH["ASD"])
        self.diskTable = self.findChild(QtWidgets.QTableWidget, "tableWidget")
        self.queueTable = self.findChild(QtWidgets.QTableWidget, "queueTable")
        self.reloadButton = self.findChild(QtWidgets.QPushButton, "reloadButton")
        self.eraseButton = self.findChild(QtWidgets.QPushButton, "eraseButton")
        self.smartButton = self.findChild(QtWidgets.QPushButton, "smartButton")
        self.cannoloButton = self.findChild(QtWidgets.QPushButton, "cannoloButton")
        self.stdProcedureButton = self.findChild(QtWidgets.QPushButton, "stdProcButton")
        self.localRadioBtn = self.findChild(QtWidgets.QRadioButton, "localRadioBtn")
        self.remoteRadioBtn = self.findChild(QtWidgets.QRadioButton, "remoteRadioBtn")
        self.hostInput = self.findChild(QtWidgets.QLineEdit, "remoteIp")
        self.portInput = self.findChild(QtWidgets.QLineEdit, "remotePort")
        self.restoreButton = self.findChild(QtWidgets.QPushButton, "restoreButton")
        self.defaultButton = self.findChild(QtWidgets.QPushButton, "defaultButton")
        self.saveButton = self.findChild(QtWidgets.QPushButton, "saveButton")
        self.ipList = self.findChild(QtWidgets.QListWidget, "ipList")
        self.findButton = self.findChild(QtWidgets.QPushButton, "findButton")
        self.cannoloLabel = self.findChild(QtWidgets.QLabel, "cannoloLabel")
        self.themeSelector = self.findChild(QtWidgets.QComboBox, "themeSelector")
        self.directoryText = self.findChild(QtWidgets.QLineEdit, "directoryText")
        self.smartLayout = self.findChild(QtWidgets.QVBoxLayout, "smartLayout")
        self.smartTabs = SmartTabs()
        self.smartLayout.addWidget(self.smartTabs)
        self.sleep_action = QtWidgets.QAction("Sleep", self)
        self.uploadToTarallo_action = QtWidgets.QAction("Upload to TARALLO", self)
        self.stop_action = QtWidgets.QAction("Stop", self)
        self.remove_action = QtWidgets.QAction("Remove", self)
        self.remove_all_action = QtWidgets.QAction("Remove All", self)
        self.remove_completed_action = QtWidgets.QAction("Remove Completed", self)
        self.remove_queued_action = QtWidgets.QAction("Remove Queued", self)
        self.info_action = QtWidgets.QAction("Info", self)
        self.asdlabel = self.findChild(QtWidgets.QLabel, "asdLabel")
        self.asdGif = QMovie(PATH["ASD"])
        self.asdGif.setScaledSize(
            QtCore.QSize().scaled(
                self.asdlabel.width(), self.asdlabel.height(), Qt.KeepAspectRatio
            )
        )
        self.asdGif.start()
        self.asdlabel.setMovie(self.asdGif)

        """ Initialization operations """
        self.set_items_functions()
        self.localServer = LocalServer()
        self.localServer.update.connect(self.server_com)
        self.show()
        self.setup()

    def on_table_select(self, selected):
        """This function set the queue table context menu buttons"""

        sel = selected.count()
        if sel == 0:
            self.stop_action.setEnabled(False)
            self.remove_action.setEnabled(False)
            self.info_action.setEnabled(False)
            self.sleep_action.setEnabled(False)
            self.uploadToTarallo_action.setEnabled(False)
        else:
            self.stop_action.setEnabled(True)
            self.remove_action.setEnabled(True)
            self.info_action.setEnabled(True)
            self.sleep_action.setEnabled(True)
            self.uploadToTarallo_action.setEnabled(True)

    # noinspection DuplicatedCode
    def set_items_functions(self):
        """This function set the widget's function to the respective widget and
        other widget's constraints"""

        # set icon
        self.setWindowIcon(QIcon(PATH["ICON"]))

        # get latest configuration
        self.latest_conf()

        # disks table
        self.diskTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.diskTable.horizontalHeader().setStretchLastSection(True)
        self.diskTable.setColumnWidth(0, 65)
        self.diskTable.setColumnWidth(1, 70)
        self.diskTable.setColumnWidth(2, 60)
        self.diskTable.horizontalHeader().setStretchLastSection(True)
        self.diskTable.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Fixed
        )
        self.diskTable.cellClicked.connect(self.greyout_buttons)
        self.diskTable.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.sleep_action.triggered.connect(self.sleep)
        self.diskTable.addAction(self.sleep_action)
        self.sleep_action.setEnabled(False)
        self.uploadToTarallo_action.triggered.connect(self.upload_to_tarallo)
        self.diskTable.addAction(self.uploadToTarallo_action)
        self.uploadToTarallo_action.setEnabled(False)

        self.diskTable.selectionModel().selectionChanged.connect(self.on_table_select)

        # queue table
        self.queueTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.queueTable.setRowCount(0)
        self.queueTable.horizontalHeader().setStretchLastSection(True)
        self.queueTable.setColumnWidth(0, 125)
        self.queueTable.setColumnWidth(2, 65)
        self.queueTable.setColumnWidth(3, 65)
        self.queueTable.setColumnWidth(4, 50)
        self.queueTable.horizontalHeader().setStretchLastSection(True)
        self.queueTable.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Fixed
        )
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
        self.remove_completed_action.triggered.connect(self.queue_clear_completed)
        self.queueTable.addAction(self.remove_completed_action)
        self.remove_completed_action.setEnabled(True)
        self.remove_queued_action.triggered.connect(self.queue_clear_queued)
        self.queueTable.addAction(self.remove_queued_action)
        self.remove_queued_action.setEnabled(True)

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
            self.cannoloLabel.setText(
                "When in remote mode, the user must insert manually the cannolo image directory."
            )
        else:
            self.cannoloLabel.setText("")

        # theme selector
        for key in self.settings.childKeys():
            if "theme" in key:
                self.themeSelector.setCurrentText(self.settings.value(key))
                self.set_theme()
        self.themeSelector.currentTextChanged.connect(self.set_theme)

    def latest_conf(self):
        """This function try to set the remote configuration used in the last
        pinolo session"""

        self.remoteMode = self.settings.value("remoteMode")
        if self.remoteMode == "False":
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
        """This method must be called in the __init__ function of the Ui class
        to initialize the pinolo session"""

        self.set_remote_mode()

        # check if the host and port field are set
        if self.host is None and self.port is None:
            message = "The host and port combination is not set.\nPlease visit the settings section."
            warning_dialog(message, dialog_type="ok")

        """
        The client try to connect to the BASILICO. If it can't and the client is in remote mode, then 
        a critical error is shown and the client goes in idle. If the client is in local mode and it cannot reach a
        BASILICO server, a new BASILICO process is instantiated.
        """
        self.client = ReactorThread(self.host, self.port, self.remoteMode)
        self.client.updateEvent.connect(self.gui_update)
        self.client.start()

    def test_badblocks(self):
        """This function send to the server a badblocks command.
        Use it only in test context."""

        print("GUI_TEST: queued_badblocks")
        try:
            self.client.send(
                f"queued_badblocks {self.testDiskTable.item(self.testDiskTable.currentRow(), 0).text().lstrip('Disk ')}"
            )
        except BaseException:
            print("GUI_TEST: Error in test_badblocks test.")

    def test_cannolo(self):
        """This function send to the server a cannolo command.
        Use it only in test context."""

        print("GUI_TEST: queued_cannolo")
        try:
            self.client.send(
                f"queued_cannolo {self.testDiskTable.item(self.testDiskTable.currentRow(), 0).text().lstrip('Disk ')}"
            )
        except BaseException:
            print("GUI_TEST: Error in cannolo test.")

    def test_sleep(self):
        """This function send to the server a queued_sleep command.
        Use it only in test context."""

        print("GUI_TEST: queued_sleep")
        try:
            self.client.send(
                f"queued_sleep {self.testDiskTable.item(self.testDiskTable.currentRow(), 0).text().lstrip('Disk ')}"
            )
        except BaseException:
            print("GUI_TEST: Error in sleep test.")

    def test_smartctl(self):
        """This function send to the server a queued_smart command.
        Use it only in test context."""

        print("GUI_TEST: queued_smartctl")
        try:
            self.client.send(
                f"queued_smartctl {self.testDiskTable.item(self.testDiskTable.currentRow(), 0).text().lstrip('Disk ')}"
            )
        except BaseException:
            print("GUI_TEST: Error in smartctl test.")

    def test_load_to_tarallo(self):
        """This function send to the server a queued_load_to_tarallo command.
        Use it only in test context."""

        print("GUI_TEST: queued_load_to_tarallo")
        try:
            self.client.send(
                f"queued_load_to_tarallo {self.testDiskTable.item(self.testDiskTable.currentRow(), 0).text().lstrip('Disk ')}"
            )
        except BaseException:
            print("GUI_TEST: Error in load to tarallo test.")

    def test_std_proc(self, cannolo_flag=True):
        """This function send to the server a list of test commands:
            - queued_badblocks
            - queued_smartctl
            - queued_cannolo (if cannolo_flag is True)
            - queued_load_to_tarallo
            - queued_sleep
        Use it only in test context."""

        self.test_badblocks()
        self.test_smartctl()
        if cannolo_flag:
            self.test_cannolo()
        self.test_load_to_tarallo()
        self.test_sleep()

    def test_std_proc_no_cannolo(self):
        """This function call the test_std_proc method, setting the cannolo_flag
        as True."""

        self.test_std_proc(cannolo_flag=False)

    def deselect(self):
        """This function clear the queue table active selection."""

        self.queueTable.clearSelection()
        self.queueTable.clearFocus()

    def queue_stop(self):
        """This function set the "stop" button behaviour on the queue table
        context menu."""

        pid = self.queueTable.item(self.queueTable.currentRow(), 0).text()
        message = "Do you want to stop the process?\nID: " + pid
        if warning_dialog(message, dialog_type="yes_no") == QtWidgets.QMessageBox.Yes:
            self.client.send(f"stop {pid}")
        self.deselect()

    def queue_remove(self):
        """This function set the "remove" button behaviour on the queue table
        context menu."""

        pid = self.queueTable.item(self.queueTable.currentRow(), 0).text()
        message = "With this action you will also stop the process (ID: " + pid + ")\n"
        message += "Do you want to proceed?"
        if warning_dialog(message, dialog_type="yes_no") == QtWidgets.QMessageBox.Yes:
            self.client.send(f"remove {pid}")
            self.queueTable.removeRow(self.queueTable.currentRow())
        self.deselect()

    def queue_clear(self):
        """This function set the "remove all" button behaviour on the queue table
        context menu."""

        self.queueTable.setRowCount(0)
        self.client.send("remove_all")

    def queue_clear_completed(self):
        """This function set the "remove completed" button behaviour on the queue table
        context menu."""

        self.queueTable.setRowCount(0)
        self.client.send("remove_completed")

    def queue_clear_queued(self):
        """This function set the "remove completed" button behaviour on the queue table
        context menu."""

        self.queueTable.setRowCount(0)
        self.client.send("remove_queued")

    def queue_info(self):
        """This function set the "info" button behaviour on the queue table
        context menu."""

        process = self.queueTable.item(self.queueTable.currentRow(), 1).text()
        message = ""
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
        """This function send to the server a sequence of commands:
        - queued_badblocks
        - queued_smartctl
        - queued_cannolo (if the cannolo flag on the dialog is checked)
        - queued_sleep
        """

        message = "Do you want to wipe all disk's data and load a fresh system image?"
        dialog = warning_dialog(message, dialog_type="yes_no_chk")
        if dialog[0] == QtWidgets.QMessageBox.Yes:
            self.erase(std=True)
            self.smart(std=True)
            if dialog[1]:
                self.cannolo(std=True)

    def erase(self, std=False):
        """This function send to the server a queued_badblocks command.
        If "std" is True it will skip the confirm dialog."""

        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                message = "There are no selected drives."
                warning_dialog(message, dialog_type="ok")
                return
            else:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            if not std:
                message = (
                    "Do you want to wipe all disk's data?\nDisk: " + self.selected_drive
                )
                if (
                    critical_dialog(message, dialog_type="yes_no")
                    != QtWidgets.QMessageBox.Yes
                ):
                    return
            self.client.send("queued_badblocks " + self.selected_drive)

        except BaseException:
            print("GUI: Error in erase Function")

    def smart(self, std=False):
        """This function send to the server a queued_smartctl command.
        If "std" is True it will skip the "no drive selected" check."""

        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type="ok")
                    return
                return
            # TODO: Add new tab for every smart requested. If drive tab exist, use it.
            drive = self.selected_drive.text().lstrip("Disk ")
            self.client.send("queued_smartctl " + drive)

        except BaseException:
            print("GUI: Error in smart function.")

    def cannolo(self, std=False):
        """This function send to the server a queued_cannolo command.
        If "std" is True it will skip the cannolo dialog."""

        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            directory = self.directoryText.text().rsplit("/", 1)[0] + "/"
            if self.selected_drive is None:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type="ok")
                    return
                return
            else:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            if not std:
                self.client.send(f"list_iso {directory}")
                self.manual_cannolo = True
                return
            print(
                f"GUI: Sending cannolo to {self.selected_drive} with {self.directoryText.text()}"
            )
            self.client.send(
                f"queued_cannolo {self.selected_drive} {self.directoryText.text()}"
            )

        except BaseException:
            print("GUI: Error in cannolo function.")

    def upload_to_tarallo(self, std=False):
        """This function send to the server a queued_upload_to_tarallo command.
        If "std" is True it will skip the confirm dialog."""

        self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
        selected_drive_id = self.diskTable.item(self.diskTable.currentRow(), 1).text()
        if selected_drive_id == "":
            message = (
                "The selected disk doesn't have a TARALLO id.\n"
                "No data will be uploaded to TARALLO."
            )
            warning_dialog(message, dialog_type="ok")
            return
        if not std:
            message = "Do you want to load the disk informations into TARALLO?"
            if (
                warning_dialog(message, dialog_type="yes_no")
                == QtWidgets.QMessageBox.No
            ):
                return
        self.selected_drive = self.selected_drive.text().lstrip("Disk ")
        self.client.send(f"queued_upload_to_tarallo {self.selected_drive}")

    def sleep(self, std=False):
        """This function send to the server a queued_sleep command.
        If "std" is True it will skip the "no drive selected" check."""

        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type="ok")
                    return
                return
            else:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            self.client.send("queued_sleep " + self.selected_drive)

        except BaseException:
            print("GUI: Error in cannolo function.")

    def set_remote_mode(self):
        """This function set all the parameters related to the client-server
        communications and other UI-related behaviours."""

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
            self.cannoloLabel.setText(
                "When in remote mode, the user must insert manually the cannolo image directory."
            )

    def refresh(self):
        """This function read the host and port inputs in the settings
        tab and try to reconnect to the server, refreshing the disk list."""

        self.host = self.hostInput.text()
        self.port = int(self.portInput.text())
        self.client.reconnect(self.host, self.port)

    def restore(self):
        """This function delete all the edits made in the host and port input
        in the settings tab."""

        self.hostInput.setText(self.host)
        self.portInput.setText(str(self.port))

    def update_queue(self, pid, drive, mode):
        """This function update the queue table with the new entries."""

        # self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        row = self.queueTable.rowCount()
        self.queueTable.insertRow(row)
        for idx, entry in enumerate(QUEUE_TABLE):
            label: Union[
                None,
                str,
                QtWidgets.QLabel,
                QtWidgets.QProgressBar,
                QtWidgets.QTableWidgetItem,
            ]
            label = None
            if entry == "ID":  # ID
                label = pid
            elif entry == "Process":  # PROCESS
                if mode == "queued_badblocks":
                    label = "Erase"
                elif mode == "queued_smartctl" or mode == "smartctl":
                    label = "Smart check"
                elif mode == "queued_cannolo":
                    label = "Cannolo"
                elif mode == "queued_sleep":
                    label = "Sleep"
                else:
                    label = "Unknown"
            elif entry == "Disk":  # DISK
                label = drive
            elif entry == "Status":  # STATUS
                if self.queueTable.rowCount() != 0:
                    label = QtWidgets.QLabel()
                    label: QtWidgets.QLabel
                    label.setPixmap(
                        QtGui.QPixmap(PATH["PENDING"]).scaled(
                            25, 25, QtCore.Qt.KeepAspectRatio
                        )
                    )
                else:
                    label: QtWidgets.QLabel
                    label.setPixmap(
                        QtGui.QPixmap(PATH["PROGRESS"]).scaled(
                            25, 25, QtCore.Qt.KeepAspectRatio
                        )
                    )
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

    def greyout_buttons(self):
        """This function greys out some buttons when they must not be used."""

        self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
        if self.selected_drive is not None:
            self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            if self.selected_drive in self.critical_mounts:
                self.statusBar().showMessage(
                    f"Disk {self.selected_drive} has critical mountpoints: some actions are restricted."
                )
                self.eraseButton.setEnabled(False)
                self.stdProcedureButton.setEnabled(False)
                self.cannoloButton.setEnabled(False)
            else:
                self.eraseButton.setEnabled(True)
                self.stdProcedureButton.setEnabled(True)
                self.cannoloButton.setEnabled(True)

        try:
            self.selected_drive = self.testDiskTable.item(
                self.testDiskTable.currentRow(), 0
            )
            if self.selected_drive is not None:
                self.selected_drive = self.selected_drive.text().lstrip("Disk ")
                if self.selected_drive in self.critical_mounts:
                    self.statusBar().showMessage(
                        f"Disk {self.selected_drive} has critical mountpoints: some actions are restricted."
                    )
                    self.testBadblocksBtn.setEnabled(False)
                    self.testCannoloBtn.setEnabled(False)
                    self.testStdProcBtn.setEnabled(False)
                    self.testStdProcNoCannoloBtn.setEnabled(False)
                else:
                    self.testBadblocksBtn.setEnabled(True)
                    self.testCannoloBtn.setEnabled(True)
                    self.testStdProcBtn.setEnabled(True)
                    self.testStdProcNoCannoloBtn.setEnabled(True)
        except Exception as exc:
            print(exc.args)

    def save_config(self):
        """This function saves the active host and port configuration in the qt settings
        file, showing them in the recent ip list."""

        ip = self.hostInput.text()
        port = self.portInput.text()
        if self.ipList.findItems(ip, Qt.MatchExactly):
            message = "Do you want to overwrite the old configuration?"
            if (
                warning_dialog(message, dialog_type="yes_no")
                == QtWidgets.QMessageBox.Yes
            ):
                self.settings.setValue("saved-" + ip, [ip, port])
        else:
            self.ipList.addItem(ip)
            self.settings.setValue("saved-" + ip, [ip, port])

    def remove_config(self):
        """This function removes the selected configuration in the recent
        ip list in the settings tab."""
        try:
            ip = self.ipList.currentItem().text()
        except:
            return
        message = "Do you want to remove the selected configuration?"
        if warning_dialog(message, dialog_type="yes_no") == QtWidgets.QMessageBox.Yes:
            for key in self.settings.childKeys():
                if ip in key:
                    self.ipList.takeItem(self.ipList.row(self.ipList.currentItem()))
                    self.settings.remove(key)

    def load_config(self):
        """This function loads the selected configuration in the recent ip
        list in the settings tab."""

        ip = self.ipList.currentItem().text()
        for key in self.settings.childKeys():
            if ip in key:
                values = self.settings.value(key)
                port = values[1]
                self.hostInput.setText(ip)
                self.portInput.setText(port)

    def default_config(self):
        """This function removes all the data from the qt settings file.
        Use with caution."""

        message = "Do you want to restore all settings to default?\nThis action is unrevocable."
        if critical_dialog(message, dialog_type="yes_no") == QtWidgets.QMessageBox.Yes:
            self.settings.clear()
            self.ipList.clear()
            self.setup()

    def find_image(self):
        """This function opens a different dialog, depending if
        the user is in local or remote mode, to search for a cannolo image."""

        # noinspection PyBroadException
        try:
            if self.remoteMode:
                directory = self.directoryText.text()
                splitted_dir = directory.rsplit("/", 1)
                if len(splitted_dir[1].split(".")) > 1:
                    self.client.send("list_iso " + directory.rsplit("/", 1)[0])
                else:
                    if directory[-1] != "/":
                        directory += "/"
                    self.client.send("list_iso " + directory)
            else:
                dialog = QtWidgets.QFileDialog()
                directory = dialog.getExistingDirectory(
                    self, "Open Directory", "/home", QtWidgets.QFileDialog.ShowDirsOnly
                )
                self.directoryText.setText(directory)

        except BaseException as ex:
            print(f"GUI: Error in smart function [{ex}]")

    def set_default_cannolo(self, directory: str, img: str):
        """This function set the default cannolo path in the settings tab."""

        if self.set_default_cannolo:
            self.statusBar().showMessage(f"Default cannolo image set as {img}.iso")
            self.directoryText.setText(directory)

    def use_cannolo_img(self, directory: str, img: str):
        """This function sends to the server a queued_cannolo with the selected drive
        and the directory of the selected cannolo image. This is specific of the
        non-standard procedure cannolo."""
        self.statusBar().showMessage(
            f"Sending cannolo to {self.selected_drive} with {img}"
        )
        self.client.send(f"queued_cannolo {self.selected_drive} {directory}")

    def set_theme(self):
        """This function gets the stylesheet of the theme and sets the widgets aspect.
        Only for the Vaporwave theme, it will search a .mp3 file that will be played in background.
        Just for the meme. asd"""

        theme = self.themeSelector.currentText()
        if theme == "Vaporwave":
            try:
                f = open("assets/vaporwave_theme.mp3")
                f.close()
                self.audio_process = Process(
                    target=playsound.playsound, args=("assets/vaporwave_theme.mp3",)
                )
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
            self.reloadButton.setIconSize(QtCore.QSize(25, 25))
            self.asd_gif_set(PATH["ASD"])
            self.cannoloLabel.setStyleSheet("color: yellow")
        elif theme == "Vaporwave":
            with open(PATH["VAPORTHEME"], "r") as file:
                self.app.setStyleSheet(file.read())
            self.reloadButton.setIcon(QIcon(PATH["VAPORWAVERELOAD"]))
            self.reloadButton.setIconSize(QtCore.QSize(50, 50))
            self.backgroundLabel.clear()
            self.asd_gif_set(PATH["ASDVAP"])
            self.cannoloLabel.setStyleSheet("color: rgb(252, 186, 3)")
        elif theme == "Asd":
            with open(PATH["ASDTHEME"], "r") as file:
                self.app.setStyleSheet(file.read())
            self.backgroundLabel = self.findChild(QtWidgets.QLabel, "backgroundLabel")
            self.movie = QMovie(PATH["ASD"])
            self.movie.setScaledSize(
                QtCore.QSize().scaled(400, 400, Qt.KeepAspectRatio)
            )
            self.movie.start()
            self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))
            self.backgroundLabel.setMovie(self.movie)
            self.reloadButton.setIconSize(QtCore.QSize(25, 25))
            self.asd_gif_set(PATH["ASD"])
            self.cannoloLabel.setStyleSheet("color: blue")
        elif theme == "WeeeOpen":
            with open(PATH["WEEETHEME"], "r") as file:
                self.app.setStyleSheet(file.read())
            self.backgroundLabel.clear()
            self.backgroundLabel.setPixmap(
                QtGui.QPixmap(PATH["WEEE"]).scaled(300, 300, QtCore.Qt.KeepAspectRatio)
            )
            self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))
            self.reloadButton.setIconSize(QtCore.QSize(25, 25))
            self.asd_gif_set(PATH["ASD"])
        elif theme == "Default":
            self.app.setStyleSheet("")
            with open(PATH["DEFAULTTHEME"], "r") as file:
                self.app.setStyleSheet(file.read())
            self.backgroundLabel.clear()
            self.reloadButton.setIcon(QIcon(PATH["RELOAD"]))
            self.reloadButton.setIconSize(QtCore.QSize(25, 25))
            self.asd_gif_set(PATH["ASD"])
            self.cannoloLabel.setStyleSheet("color: blue")

    def asd_gif_set(self, dir: str):
        """This function sets the asd gif for the settings tab."""

        self.asdGif = QMovie(dir)
        self.asdGif.setScaledSize(
            QtCore.QSize().scaled(
                self.asdlabel.width(), self.asdlabel.height(), Qt.KeepAspectRatio
            )
        )
        self.asdGif.start()
        self.asdlabel.setMovie(self.asdGif)

    def server_com(self, cmd: str, st2: str):
        """This function tries to reconnect the client to the local server.
        It will try to find out if the server is already running in background."""

        if cmd == "SERVER_READY":
            print("GUI: Local server loaded. Connecting...")
            self.client.reconnect(self.host, self.port)
        elif cmd == "SERVER_ALREADY_UP":
            print("GUI: Local server already up. Reconnecting...")
            self.client.reconnect(self.host, self.port)

    def check_disk_usage(self):
        disks_rows = self.diskTable.rowCount()
        queue_rows = self.queueTable.rowCount()
        if queue_rows > 0 and disks_rows > 0:
            for disk_row in range(disks_rows + 1):
                disk_label = self.diskTable.item(disk_row, 0)
                if disk_label is not None:
                    disk_label = disk_label.text()
                    for queue_row in range(queue_rows + 1):
                        queue_disk_label = self.queueTable.item(queue_row, 2)
                        queue_progress = self.queueTable.cellWidget(queue_row, 4)
                        if queue_disk_label is not None and queue_progress is not None:
                            queue_disk_label = queue_disk_label.text()
                            queue_progress = queue_progress.findChild(
                                QtWidgets.QProgressBar
                            ).value()
                            if queue_disk_label == disk_label and queue_progress != 100:
                                self.diskTable.item(disk_row, 0).setBackground(
                                    Qt.yellow
                                )
                                self.diskTable.item(disk_row, 0).setForeground(Qt.black)
                                break
                        if queue_row == queue_rows:
                            self.diskTable.item(disk_row, 0).setBackground(
                                Qt.transparent
                            )

    def gui_update(self, cmd: str, params: str):
        """
        This function gets all the server responses and update, if possible, the UI. "

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
            print(
                f"GUI: Ignored exception while parsing {cmd}, expected JSON but this isn't: {params}"
            )

        if cmd == "queue_status" or cmd == "get_queue":
            if cmd == "queue_status":
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
                        self.update_queue(
                            pid=param["id"],
                            drive=param["target"],
                            mode=param["command"],
                        )
                        rows += 1
                progress_bar = self.queueTable.cellWidget(row, 4).findChild(
                    QtWidgets.QProgressBar
                )
                status_cell = self.queueTable.cellWidget(row, 3)
                progress_bar.setValue(int(param["percentage"]))
                if param["stale"]:
                    pass
                elif param["stopped"]:
                    # TODO: we don't have an icon for this, maybe we should
                    status_cell.setPixmap(
                        QtGui.QPixmap(PATH["STOP"]).scaledToHeight(
                            25, Qt.SmoothTransformation
                        )
                    )
                elif param["error"]:
                    status_cell.setPixmap(
                        QtGui.QPixmap(PATH["ERROR"]).scaledToHeight(
                            25, Qt.SmoothTransformation
                        )
                    )
                elif param["finished"]:  # and not error
                    status_cell.setPixmap(
                        QtGui.QPixmap(PATH["OK"]).scaledToHeight(
                            25, Qt.SmoothTransformation
                        )
                    )
                elif param["started"]:
                    status_cell.setPixmap(
                        QtGui.QPixmap(PATH["PROGRESS"]).scaledToHeight(
                            25, Qt.SmoothTransformation
                        )
                    )
                else:
                    status_cell.setPixmap(
                        QtGui.QPixmap(PATH["PENDING"]).scaledToHeight(
                            25, Qt.SmoothTransformation
                        )
                    )

        elif cmd == "get_disks":
            drives = params
            if len(drives) <= 0:
                self.diskTable.setRowCount(0)
                return
            # compile disks table with disks list
            rows = 0
            for d in drives:
                d: dict
                # if "[BOOT]" in d["mountpoint"]:
                #     continue
                rows += 1
                self.diskTable.setRowCount(rows)
                try:
                    self.testDiskTable.setRowCount(rows)
                except AttributeError:
                    print("Test mode disabled: testDiskTable not loaded.")

                self.diskTable.setItem(rows - 1, 0, QTableWidgetItem(d["path"]))
                try:
                    self.testDiskTable.setItem(rows - 1, 0, QTableWidgetItem(d["path"]))
                except:
                    pass

                self.diskTable.setItem(rows - 1, 1, QTableWidgetItem(d["code"]))
                self.diskTable.setItem(
                    rows - 1,
                    2,
                    QTableWidgetItem(str(int(int(d["size"]) / 1000000000)) + " GB"),
                )
                try:
                    self.testDiskTable.setItem(rows - 1, 1, QTableWidgetItem(d["code"]))
                    self.testDiskTable.setItem(
                        rows - 1,
                        2,
                        QTableWidgetItem(str(int(int(d["size"]) / 1000000000)) + " GB"),
                    )
                except:
                    pass
                if d["has_critical_mounts"]:
                    self.critical_mounts.append(d["path"])
                    print(self.critical_mounts)

        elif cmd == "smartctl" or cmd == "queued_smartctl":
            text = ("Smartctl output:\n " + params["output"]).splitlines()
            tab_count = self.smartTabs.count()
            tab = 0
            for tab in range(tab_count + 1):
                if self.smartTabs.tabText(tab) == params["disk"]:
                    message = "Il tab per il dosco esiste già asd.\nVuoi sovrascrivere l'output?"
                    if (
                        warning_dialog(message, dialog_type="yes_no")
                        == QtWidgets.QMessageBox.Yes
                    ):
                        self.smartTabs.removeTab(tab)
                        self.smartTabs.add_tab(
                            params["disk"], params["status"], params["updated"], text
                        )
                    break
                elif tab == tab_count:
                    self.smartTabs.add_tab(
                        params["disk"], params["status"], params["updated"], text
                    )

        elif cmd == "connection_failed":
            message = params["reason"]
            if not self.remoteMode:
                print("GUI: Connection Failed: Local server not running.")
                print("GUI: Trying to start local server...")
                self.localServer.start()
                return
            if "Connection was refused by other side" in message:
                message = (
                    "Cannot find BASILICO server.\nCheck if it's running in the "
                    "targeted machine."
                )
            warning_dialog(message, dialog_type="ok")

        elif cmd == "connection_lost":
            self.statusBar().showMessage(
                f"⚠ Connection lost. Press the reload button to reconnect."
            )
            self.queueTable.setRowCount(0)
            self.diskTable.setRowCount(0)

        elif cmd == "connection_made":
            self.statusBar().showMessage(
                f"Connected to {params['host']}:{params['port']}"
            )

        elif cmd == "list_iso":
            self.dialog = CannoloDialog(PATH, params)
            if self.manual_cannolo:
                self.dialog.update.connect(self.use_cannolo_img)
                self.manual_cannolo = False
            else:
                self.dialog.update.connect(self.set_default_cannolo)

        elif cmd == "error":
            message = params["message"]
            critical_dialog(message, dialog_type="ok")

        elif cmd == "error_that_can_be_manually_fixed":
            message = params["message"]
            warning_dialog(message, dialog_type="ok")

        self.check_disk_usage()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        """This function is called when the window is closed.
        It will save all the latest settings parameters into the QT settings file and
        terminate all the active audio processes."""

        self.settings.setValue("remoteMode", str(self.remoteMode))
        self.settings.setValue("remoteIp", self.hostInput.text())
        self.settings.setValue("remotePort", self.portInput.text())
        self.settings.setValue("cannoloDir", self.directoryText.text())
        self.settings.setValue("theme", self.themeSelector.currentText())
        self.client.stop(self.remoteMode)
        try:
            self.audio_process.terminate()
        except:
            print("No audio process running.")


class LocalServer(QThread):
    update = QtCore.pyqtSignal(str, str, name="update")

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.server: subprocess.Popen
        self.server = None
        self.running = False

    def run(self):
        if not self.running:
            self.server = subprocess.Popen(
                ["python", PATH["SERVER"]],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            while "Listening on" not in self.server.stderr.readline().decode("utf-8"):
                pass
            self.running = True
            self.update.emit("SERVER_READY", "")
        else:
            self.update.emit("SERVER_ALREADY_UP", "")

    def stop(self):
        if self.running:
            self.server.terminate()
        self.running = False


def main():
    # noinspection PyBroadException
    try:
        load_dotenv(PATH["ENV"])
        app = QtWidgets.QApplication(sys.argv)
        window = Ui(app)
        app.exec_()

    except KeyboardInterrupt:
        print("KeyboardInterrupt")

    except BaseException:
        print(traceback.print_exc(file=sys.stdout))


if __name__ == "__main__":
    main()
