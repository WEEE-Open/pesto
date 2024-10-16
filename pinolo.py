#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
from client import *
from utilities import *
from widgets.smart import SmartWidget
from widgets.settings import SettingsDialog
from typing import Union
from dotenv import load_dotenv
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QMovie, QDesktopServices, QPixmap, QCloseEvent, QColor
from PyQt5.QtCore import Qt, QSettings, QSize, pyqtSignal, QThread, QUrl
from PyQt5.QtWidgets import (
    QTableWidgetItem,
    QAction,
    QPushButton,
    QTableWidget,
    QMenu,
    QMessageBox,
    QMainWindow,
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QVBoxLayout,
    QProgressBar,
    QWidget,
    QSplitter,
)
from diff_dialog import DiffWidget
from variables import *
from datetime import datetime, timedelta
import sys
import traceback

absolute_path(PATH)


# UI class
class PinoloMainWindow(QMainWindow):
    def __init__(self, app: QApplication) -> None:
        super(PinoloMainWindow, self).__init__()
        uic.loadUi(PATH["UI"], self)
        self.app = app
        self.host = DEFAULT_IP
        self.port = DEFAULT_PORT
        self.cannoloDir = ""
        self.remoteMode = False
        self.manual_cannolo = False
        self.active_theme = None
        self.dialog = None
        self.pixmap = None
        self.pixmapAspectRatio = None
        self.pixmapResizingNeeded = None
        self.selected_drive = None
        self.timeKeeper = {}

        self.critical_mounts = []
        self.smart_results = {}

        self.settings = QSettings("WEEE-Open", "PESTO")
        self.client = ReactorThread(self.host, self.port, self.remoteMode)

        """ Utilities Widgets """
        self.latest_conf()
        self.diff_widgets = {}
        self.smart_widgets = {}
        self.settingsDialog = SettingsDialog(self.host, self.port, self.remoteMode, self.cannoloDir, self.settings, self.client)
        self.settingsDialog.update.connect(self.update_settings)

        """ Defining all items in GUI """
        self.gif = QMovie(PATH["ASD"])
        self.splitter = self.findChild(QSplitter, "splitter")
        self.diskTable = self.findChild(QTableWidget, "diskTable")
        self.queueTable = self.findChild(QTableWidget, "queueTable")
        self.refreshButton = self.findChild(QPushButton, "refreshButton")
        self.eraseButton = self.findChild(QPushButton, "eraseButton")
        self.smartButton = self.findChild(QPushButton, "smartButton")
        self.cannoloButton = self.findChild(QPushButton, "cannoloButton")
        self.stdProcedureButton = self.findChild(QPushButton, "stdProcButton")

        """ Defining menu actions """
        self.newSessionAction = self.findChild(QAction, "newSessionAction")
        self.refreshAction = self.findChild(QAction, "refreshAction")
        self.exitAction = self.findChild(QAction, "exitAction")
        self.networkSettingsAction = self.findChild(QAction, "networkSettingsAction")
        self.themeMenu = self.findChild(QMenu, "themeMenu")
        self.aboutUsAction = self.findChild(QAction, "actionAboutUs")
        self.sourceCodeAction = self.findChild(QAction, "actionSourceCode")
        self.versionAction = self.findChild(QAction, "actionVersion")

        """ Defining context menu actions """
        self.sleep_action = QAction("Sleep", self)
        self.uploadToTarallo_action = QAction("Upload to TARALLO", self)
        self.showSmartData_Action = QAction("Show SMART data", self)
        self.umount_action = QAction("Umount disk", self)
        self.stop_action = QAction("Stop", self)
        self.remove_action = QAction("Remove", self)
        self.remove_all_action = QAction("Remove All", self)
        self.remove_completed_action = QAction("Remove Completed", self)
        self.remove_queued_action = QAction("Remove Queued", self)
        self.info_action = QAction("Info", self)

        """ Initialization operations """
        self.set_items_functions()
        self.localServer = LocalServer()
        self.localServer.update.connect(self.server_com)
        self.show()
        self.setup()

    def setup(self):
        """This method must be called in __init__ function of Ui class
        to initialize pinolo session"""

        # Check if the host and port field are set
        if self.host is None and self.port is None:
            message = "The host and port combination is not set.\nPlease visit the settings section."
            warning_dialog(message, dialog_type="ok")

        # Start client thread
        self.client = ReactorThread(self.host, self.port, self.remoteMode)
        self.client.updateEvent.connect(self.gui_update)
        self.client.start()

        # Actions setup
        action = list()
        action.append(self.themeMenu.addAction("Default"))
        action[-1].triggered.connect(lambda: self.set_theme("default"))
        for theme_file in os.listdir(PATH["THEMES"]):
            theme = theme_file.rstrip(".css")
            action.append(self.themeMenu.addAction(theme))
            action[-1].triggered.connect((lambda t: lambda: self.set_theme(t))(theme))

    def update_settings(self, host: str, port: int, remote_mode: bool, cannoloDir: str):
        self.host = host
        self.port = port
        self.remoteMode = remote_mode
        self.cannoloDir = cannoloDir

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

        # menu actions
        self.newSessionAction.triggered.connect(self.new_session)
        self.refreshAction.triggered.connect(self.refresh)
        self.exitAction.triggered.connect(self.close)
        self.networkSettingsAction.triggered.connect(self.open_settings)
        self.aboutUsAction.triggered.connect(self.open_website)
        self.sourceCodeAction.triggered.connect(self.open_source_code)
        self.versionAction.triggered.connect(self.show_version)

        # disk table
        self.diskTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.diskTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.diskTable.resizeColumnToContents(1)
        self.diskTable.setColumnWidth(1, self.diskTable.columnWidth(1) + 40)
        self.diskTable.resizeColumnToContents(2)
        self.diskTable.setColumnWidth(2, self.diskTable.columnWidth(2) + 20)
        self.diskTable.cellClicked.connect(self.greyout_buttons)
        self.diskTable.setContextMenuPolicy(Qt.ActionsContextMenu)

        # disk table actions
        self.sleep_action.triggered.connect(self.sleep)
        self.diskTable.addAction(self.sleep_action)
        self.sleep_action.setEnabled(False)
        self.uploadToTarallo_action.triggered.connect(self.upload_to_tarallo_selection)
        self.diskTable.addAction(self.uploadToTarallo_action)
        self.showSmartData_Action.triggered.connect(self.show_smart_data)
        self.diskTable.addAction(self.showSmartData_Action)
        self.uploadToTarallo_action.setEnabled(False)
        self.diskTable.addAction(self.umount_action)
        self.umount_action.triggered.connect(self.umount_disk)

        self.diskTable.selectionModel().selectionChanged.connect(self.on_table_select)

        # queue table
        self.queueTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queueTable.setRowCount(0)
        self.resize_queue_table_to_contents()
        self.queueTable.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

        # queue table actions
        self.queueTable.setContextMenuPolicy(Qt.ActionsContextMenu)
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

        # refresh button
        self.refreshButton.clicked.connect(self.refresh)

        # erase button
        self.eraseButton.clicked.connect(self.erase)

        # smart button
        self.smartButton.clicked.connect(self.smart)

        # cannolo button
        self.cannoloButton.clicked.connect(self.cannolo)

        # standard procedure button
        self.stdProcedureButton.clicked.connect(self.std_procedure)

        # find button
        # self.findButton.clicked.connect(self.find_image)

        # cannolo label

        # if self.remoteMode:
        #     self.cannoloLabel.setText(
        #         "When in remote mode, the user must insert manually the cannolo image directory."
        #     )
        # else:
        #     self.cannoloLabel.setText("")

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
                self.cannoloDir = self.settings.value("cannoloDir")
            except ValueError:
                if self.host is None:
                    self.host = "127.0.0.1"
                self.port = 1030
            except TypeError:
                if self.host is None:
                    self.host = "127.0.0.1"
                self.port = 1030

    @staticmethod
    def new_session():
        os.popen("python pinolo.py")

    def open_settings(self):
        self.settingsDialog.show()

    def open_url(self, url_type: str):
        url = QUrl(url_type)
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "Cannot Open Url", f"Could not open url {url_type}")

    def open_website(self):
        self.open_url(URL["website"])

    def open_source_code(self):
        self.open_url(URL["source_code"])

    def show_version(self):
        QMessageBox.about(self, "Version", f"Pesto v{VERSION}")

    def deselect(self):
        """This function clear the queue table active selection."""

        self.queueTable.clearSelection()
        self.queueTable.clearFocus()

    def queue_stop(self):
        """This function set the "stop" button behaviour on the queue table
        context menu."""

        pid = self.queueTable.item(self.queueTable.currentRow(), 0).text()
        message = "Do you want to stop the process?\nID: " + pid
        if warning_dialog(message, dialog_type="yes_no") == QMessageBox.Yes:
            self.client.send(f"stop {pid}")
        self.deselect()

    def queue_remove(self):
        """This function set the "remove" button behaviour on the queue table
        context menu."""

        pid = self.queueTable.item(self.queueTable.currentRow(), 0).text()
        message = "With this action you will also stop the process (ID: " + pid + ")\n"
        message += "Do you want to proceed?"
        if warning_dialog(message, dialog_type="yes_no") == QMessageBox.Yes:
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

        rows = self.queueTable.rowCount()
        offset = 0
        for row in range(0, rows):
            item = self.queueTable.cellWidget(row - offset, 3)
            status = item.objectName()
            if status == QUEUE_COMPLETED:
                self.queueTable.removeRow(row - offset)
                offset += 1

        self.client.send("remove_completed")

    def queue_clear_queued(self):
        """This function set the "remove completed" button behaviour on the queue table
        context menu."""

        rows = self.queueTable.rowCount()
        offset = 0
        for row in range(0, rows):
            item = self.queueTable.cellWidget(row - offset, 3)
            status = item.objectName()
            if status == QUEUE_QUEUED:
                self.queueTable.removeRow(row - offset)
                offset += 1
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

    def umount_disk(self):
        dialog = warning_dialog(
            "Are you really sure you want to umount this disk?\nThis is generally not a good idea, proceed only if you are really sure of what are you doing.",
            "yes_no"
                           )

        if dialog == QMessageBox.Yes:
            drives = self.get_multiple_drive_selection()
            for drive in drives:
                self.client.send("queued_umount " + drive)

    def get_multiple_drive_selection(self):
        """This method returns a list with the names of the selected drives on disk_table"""
        drives = []
        selected_rows = self.diskTable.selectionModel().selectedRows()
        for row in selected_rows:
            drives.append(row.data())

        return drives

    def get_selected_drive_rows(self):
        """
        Get a list of lists representing the table, with each full row that has at least one selected cell
        :return:
        """
        encountered_rows = set()
        rows = []
        self.diskTable: QtWidgets.QTableWidget
        for selectedIndex in self.diskTable.selectedIndexes():
            r = selectedIndex.row()
            if r in encountered_rows:
                continue
            encountered_rows.add(r)

            row = []
            cc = self.diskTable.columnCount()
            for c in range(cc):
                row.append(self.diskTable.item(r, c).text())
            rows.append(row)

        return rows

    def std_procedure(self):
        """This function send to the server a sequence of commands:
        - queued_badblocks
        - queued_smartctl
        - queued_cannolo (if the cannolo flag on the dialog is checked)
        - queued_sleep
        """

        message = "Do you want to wipe all disk's data and load a fresh system image?"
        dialog = warning_dialog(message, dialog_type="yes_no_chk")
        if dialog[0] == QMessageBox.Yes:
            drives = self.get_multiple_drive_selection()
            for drive in drives:
                if drive[1] == "":
                    # TODO: allow to enter ID manually?
                    message = f"{drive[0]} disk doesn't have a TARALLO id.\n" "Would you like to create the item on TARALLO?"
                    dialog_result = warning_dialog(message, dialog_type="yes_no_cancel")
                    if dialog_result == QMessageBox.Yes:
                        self.upload_to_tarallo(std=True, drive=drive[0])
                    elif dialog_result == QMessageBox.Cancel:
                        continue
            self.erase(std=True, drives=drives)
            self.smart(std=True, drives=drives)
            if dialog[1]:
                self.cannolo(std=True, drives=drives)

    @staticmethod
    def get_wipe_disks_message(drives):
        if len(drives) > 1:
            message = f"Do you want to wipe these disks?"
            for drive in drives:
                message += f"\n{drive[0]}"
        elif len(drives) > 0:
            message = f"Do you want to wipe {drives[0][0]}?"
        else:
            message = f"Do you want to wipe selected disks?"
        return message

    def erase(self, std=False, drives=None):
        """This function send to the server a queued_badblocks command.
        If "std" is True it will skip the confirm dialog."""

        # noinspection PyBroadException
        try:
            if drives is None:
                drives = self.get_multiple_drive_selection()

            drives_qty = len(drives)
            if drives_qty == 0:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type="ok")
                    return
                return
            if not std:
                message = f"Do you want to wipe all disk's data?\n"
                if drives_qty > 1:
                    message += "Disks:"
                    for drive in drives:
                        message += f" {drive[0]}"
                else:
                    message += f"Disk: {drives[0][0]}"
                if critical_dialog(message, dialog_type="yes_no") != QMessageBox.Yes:
                    return
            for drive in drives:
                self.client.send("queued_badblocks " + drive[0])

        except BaseException:
            print("GUI: Error in erase Function")

    def smart(self, std=False, drives=None):
        """This function send to the server a queued_smartctl command.
        If "std" is True it will skip the "no drive selected" check."""

        # noinspection PyBroadException
        try:
            if drives is None:
                drives = self.get_multiple_drive_selection()
            drives_qty = len(drives)
            if drives_qty == 0:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type="ok")
                    return
                return
            for drive in drives:
                self.client.send("queued_smartctl " + drive[0])

        except BaseException:
            print("GUI: Error in smart function.")

    def show_smart_data(self):
        # noinspection PyBroadException
        try:
            self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
            if self.selected_drive is None:
                return
            else:
                self.selected_drive = self.selected_drive.text()
            if self.selected_drive in self.smart_results:
                self.smart_widgets[self.selected_drive] = SmartWidget(self.selected_drive, self.smart_results[self.selected_drive])
                self.smart_widgets[self.selected_drive].close_signal.connect(self.remove_smart_widget)

        except BaseException as exc:
            print("GUI: Error in show_smart_data function.")

    def remove_smart_widget(self, drive: str):
        del self.smart_widgets[drive]

    def show_diff_widget(self, drive: str, features: str):
        self.diff_widgets["/dev/sda"] = DiffWidget("/dev/sda", features)
        self.diff_widgets["/dev/sda"].close_signal.connect(self.remove_diff_widget)

    def remove_diff_widget(self, drive: str):
        del self.diff_widgets[drive]

    def cannolo(self, std=False, drives=None):
        """This function send to the server a queued_cannolo command.
        If "std" is True it will skip the cannolo dialog."""

        # noinspection PyBroadException
        try:
            if drives is None:
                drives = self.get_multiple_drive_selection()
            drives_qty = len(drives)
            directory = self.cannoloDir.rsplit("/", 1)[0] + "/"
            if drives_qty == 0:
                if not std:
                    message = "There are no selected drives."
                    warning_dialog(message, dialog_type="ok")
                    return
                return
            if not std:
                self.client.send(f"list_iso {directory}")
                self.manual_cannolo = True
                return
            for drive in drives:
                print(f"GUI: Sending cannolo to {drive[0]} with {self.cannoloDir}")
                self.client.send(f"queued_cannolo {drive[0]} {self.cannoloDir}")

        except BaseException:
            print("GUI: Error in cannolo function.")

    def upload_to_tarallo_selection(self, std: bool = False):
        # TODO: check if it's really working
        # for row in self.get_selected_drive_rows():
        # if row[1] == "":
        # self.upload_to_tarallo(row[0])
        # self.selected_drive = self.selected_drive.text();
        self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)

        if not std:
            if self.diskTable.item(self.diskTable.currentRow(), 1).text() != "":
                message = f"The drive {self.selected_drive.text()} already has a TARALLO id."
                warning_dialog(message, dialog_type="ok")
                return
            message = "Do you want to load the disk informations into TARALLO?"
            if warning_dialog(message, dialog_type="yes_no") == QMessageBox.No:
                return
        elif self.diskTable.item(self.diskTable.currentRow(), 1).text() != "":
            return
        loc, ok = input_dialog("Location")

        # If no location is provided or cancel is selected,
        # cancel the operation
        if not ok or loc == "":
            message = "Canceled upload"
            info_dialog(message)
            return

        if self.selected_drive is None:
            self.client.send(f"queued_upload_to_tarallo {self.selected_drive.text()}")
        self.client.send(f"queued_upload_to_tarallo {self.selected_drive.text()} {loc}")

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

    def refresh(self):
        """This function read the host and port inputs in the settings
        tab and try to reconnect to the server, refreshing the disk list."""

        self.client.reconnect(self.host, self.port)

    def update_queue(self, pid, drive, mode):
        """This function update the queue table with the new entries."""

        # self.queueTable.setRowCount(self.queueTable.rowCount() + 1)
        row = self.queueTable.rowCount()
        self.queueTable.insertRow(row)
        for idx, entry in enumerate(QUEUE_TABLE):
            label: Union[
                None,
                str,
                QLabel,
                QProgressBar,
                QTableWidgetItem,
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
                elif mode == "queued_upload_to_tarallo":
                    label = "Upload"
                else:
                    label = "Unknown"
            elif entry == "Disk":  # DISK
                label = drive
            elif entry == "Status":  # STATUS
                if self.queueTable.rowCount() != 0:
                    label = QLabel()
                    label: QLabel
                    label.setPixmap(QPixmap(PATH["PENDING"]).scaled(25, 25, Qt.KeepAspectRatio))
                    label.setObjectName(QUEUE_QUEUED)
                else:
                    label: QLabel
                    label.setPixmap(QPixmap(PATH["PROGRESS"]).scaled(25, 25, Qt.KeepAspectRatio))
                    label.setObjectName(QUEUE_PROGRESS)
            elif entry == "Eta":
                label = "N/D"
            elif entry == "Progress":  # PROGRESS
                label = QProgressBar()
                label.setValue(0)
                label.setMaximum(100 * PROGRESS_BAR_SCALE)

            if entry in ["ID", "Process", "Disk"]:
                label = QTableWidgetItem(label)
                label: QTableWidgetItem
                label.setTextAlignment(Qt.AlignCenter)
                self.queueTable.setItem(row, idx, label)
            elif entry == "Status":
                label.setAlignment(Qt.AlignCenter)
                self.queueTable.setCellWidget(row, idx, label)
            elif entry == "Eta":
                label = QLabel(label)
                label.setAlignment(Qt.AlignCenter)
                self.queueTable.setCellWidget(row, idx, label)
            else:
                label.setAlignment(Qt.AlignCenter)
                layout = QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(label)
                widget = QWidget()
                widget.setLayout(layout)
                self.queueTable.setCellWidget(row, idx, widget)

    def greyout_buttons(self):
        """This function greys out some buttons when they must not be used."""

        self.selected_drive = self.diskTable.item(self.diskTable.currentRow(), 0)
        if self.selected_drive is not None:
            self.selected_drive = self.selected_drive.text().lstrip("Disk ")
            if self.selected_drive in self.critical_mounts:
                self.statusBar().showMessage(f"Disk {self.selected_drive} has critical mountpoints: some actions are restricted.")
                self.eraseButton.setEnabled(False)
                self.stdProcedureButton.setEnabled(False)
                self.cannoloButton.setEnabled(False)
            else:
                self.eraseButton.setEnabled(True)
                self.stdProcedureButton.setEnabled(True)
                self.cannoloButton.setEnabled(True)

    def use_cannolo_img(self, directory: str, img: str):
        """This function sends to the server a queued_cannolo with the selected drive
        and the directory of the selected cannolo image. This is specific of the
        non-standard procedure cannolo."""

        drives = self.get_multiple_drive_selection()
        ids = ""
        for drive in drives:
            ids += f"{drive[0]}, "
        ids.rstrip(", ")
        self.statusBar().showMessage(f"Sending cannolo to {ids} with {img}")
        for drive in drives:
            self.client.send(f"queued_cannolo {drive[0]} {directory}")

    def set_theme(self, theme: str):
        """This function gets the stylesheet of the theme and sets the widgets aspect.
        Only for the Vaporwave theme, it will search a .mp3 file that will be played in background.
        Just for the meme. asd"""

        self.pixmap = None

        if theme == "default":
            self.app.setStyleSheet("")
            self.app.setStyleSheet("QWidget {" "font-size: 10pt;" "}")
            self.asd_gif_set(PATH["ASD"])
            self.settingsDialog.cannoloLabel.setStyleSheet("color: blue")
            self.active_theme = "default"
            self.refreshButton.setIcon(QIcon(PATH["RELOAD"]))
        else:
            with open(f"{PATH['THEMES']}{theme}.css", "r") as file:
                self.app.setStyleSheet(file.read())
            if self.active_theme == "Vaporwave":
                self.asd_gif_set(PATH["ASDVAP"])
                self.refreshButton.setIcon(QIcon(PATH["VAPORWAVERELOAD"]))
                self.refreshButton.setIconSize(QSize(50, 50))
            else:
                self.refreshButton.setIcon(QIcon(PATH["RELOAD"]))
                self.refreshButton.setIconSize(QSize(25, 25))
                self.asd_gif_set(PATH["ASD"])

        self.settings.setValue("last_theme", theme)
        self.active_theme = theme

    def asd_gif_set(self, dir: str):
        """This function sets the asd gif for the settings tab."""

        self.settingsDialog.asdGif = QMovie(dir)
        self.settingsDialog.asdGif.setScaledSize(
            QSize().scaled(self.settingsDialog.asdlabel.width(), self.settingsDialog.asdlabel.height(), Qt.KeepAspectRatio)
        )
        self.settingsDialog.asdGif.start()
        self.settingsDialog.asdlabel.setMovie(self.settingsDialog.asdGif)

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
                        queue_progress = self.queueTable.cellWidget(queue_row, 5)
                        if self.diskTable.item(disk_row, 0).text() in self.critical_mounts:
                            continue
                        if queue_disk_label is not None and queue_progress is not None:
                            queue_disk_label = queue_disk_label.text()
                            queue_progress = queue_progress.findChild(QProgressBar).value()
                            if queue_disk_label == disk_label and queue_progress != (100 * PROGRESS_BAR_SCALE):
                                self.diskTable.item(disk_row, 0).setBackground(Qt.yellow)
                                self.diskTable.item(disk_row, 0).setForeground(Qt.black)
                                break
                        if queue_row == queue_rows:
                            default_foreground = self.diskTable.item(disk_row, 1).foreground()
                            self.diskTable.item(disk_row, 0).setBackground(Qt.transparent)
                            self.diskTable.item(disk_row, 0).setForeground(default_foreground)

    def set_disk_table_item(self, table: QTableWidget, row: int, drive: dict):
        table.setRowCount(row + 1)
        table.setItem(row, 0, QTableWidgetItem(drive["path"]))
        table.setItem(row, 1, QTableWidgetItem(drive["code"]))
        table.setItem(
            row,
            2,
            QTableWidgetItem(str(int(int(drive["size"]) / 1000000000)) + " GB"),
        )
        if drive["mountpoint"]:
            self.critical_mounts.append(drive["path"])
            item = table.item(row, 0)
            item.setBackground(QColor(255, 165, 0, 255))
            item.setForeground(Qt.black)
            item.setToolTip("Disk has critical mountpoints. Some action are restricted. Unmount manually and refresh.")

    def resize_queue_table_to_contents(self):
        for col in range(self.queueTable.columnCount() - 1):
            self.queueTable.resizeColumnToContents(col)
            self.queueTable.setColumnWidth(col, self.queueTable.columnWidth(col) + 20)

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
            print(f"GUI: Ignored exception while parsing {cmd}, expected JSON but this isn't: {params}")

        match cmd:
            case "queue_status" | "get_queue":
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
                    progress_bar = self.queueTable.cellWidget(row, 5).findChild(QProgressBar)
                    status_cell = self.queueTable.cellWidget(row, 3)
                    eta_cell = self.queueTable.cellWidget(row, 4)
                    if param["id"] in self.timeKeeper:
                        deltatime = (datetime.now() - self.timeKeeper[param["id"]]["time"]).seconds
                        deltaperc = param["percentage"] - self.timeKeeper[param["id"]]["perc"]
                        try:
                            seconds = (100 - param["percentage"]) / (deltaperc / deltatime)
                            eta = str(timedelta(seconds=seconds)).split(".")[0]
                        except ZeroDivisionError:
                            eta = eta_cell.text()
                        eta_cell.setText(eta)
                    progress_bar.setValue(int(param["percentage"] * PROGRESS_BAR_SCALE))
                    self.timeKeeper[param["id"]] = {"perc": param["percentage"], "time": datetime.now()}

                    if param["stale"]:
                        pass
                    elif param["stopped"]:
                        # TODO: we don't have an icon for this, maybe we should
                        status_cell.setPixmap(QPixmap(PATH["STOP"]).scaledToHeight(25, Qt.SmoothTransformation))
                        status_cell.setObjectName(QUEUE_COMPLETED)
                    elif param["error"]:
                        status_cell.setPixmap(QPixmap(PATH["ERROR"]).scaledToHeight(25, Qt.SmoothTransformation))
                        status_cell.setObjectName(QUEUE_COMPLETED)
                    elif param["finished"]:  # and not error
                        status_cell.setPixmap(QPixmap(PATH["OK"]).scaledToHeight(25, Qt.SmoothTransformation))
                        status_cell.setObjectName(QUEUE_COMPLETED)
                    elif param["started"]:
                        status_cell.setPixmap(QPixmap(PATH["PROGRESS"]).scaledToHeight(25, Qt.SmoothTransformation))
                        status_cell.setObjectName(QUEUE_PROGRESS)
                        self.resize_queue_table_to_contents()
                    else:
                        status_cell.setPixmap(QPixmap(PATH["PENDING"]).scaledToHeight(25, Qt.SmoothTransformation))
                        status_cell.setObjectName(QUEUE_QUEUED)

                    if "text" in param:
                        status_cell.setToolTip(param["text"])

            case "get_disks":
                drives = params
                if len(drives) <= 0:
                    self.diskTable.setRowCount(0)
                    return
                    # compile disks table with disks list
                for row, d in enumerate(drives):
                    d: dict
                    self.set_disk_table_item(self.diskTable, row, d)
                self.diskTable.resizeColumnToContents(0)
                self.diskTable.resizeColumnToContents(1)

            case "smartctl" | "queued_smartctl":
                self.smart_results[params["disk"]] = {"output": params["output"], "status": params["status"]}

            case " connection_failed":
                message = params["reason"]
                if not self.remoteMode:
                    print("GUI: Connection Failed: Local server not running.")
                    print("GUI: Trying to start local server...")
                    self.localServer.start()
                    return
                if "Connection was refused by other side" in message:
                    message = "Cannot find BASILICO server.\nCheck if it's running in the " "targeted machine."
                warning_dialog(message, dialog_type="ok")

            case "connection_lost":
                self.statusBar().showMessage(f"⚠ Connection lost. Press the reload button to reconnect.")
                self.queueTable.setRowCount(0)
                self.diskTable.setRowCount(0)

            case "connection_made":
                self.statusBar().showMessage(f"Connected to {params['host']}:{params['port']}")

            case "list_iso":
                self.dialog = CannoloDialog(self.settingsDialog, PATH, params)
                if self.manual_cannolo:
                    self.dialog.update.connect(self.use_cannolo_img)
                    self.manual_cannolo = False
                else:
                    self.dialog.update.connect(self.settingsDialog.set_default_cannolo)

            case "error":
                message = f"{params['message']}"
                if "command" in params:
                    message += f":\n{params['command']}"
                critical_dialog(message, dialog_type="ok")

            case "error_that_can_be_manually_fixed":
                message = params["message"]
                warning_dialog(message, dialog_type="ok")

        self.check_disk_usage()

    def closeEvent(self, a0: QCloseEvent) -> None:
        """This function is called when the window is closed.
        It will save all the latest settings parameters into the QT settings file and
        terminate all the active audio processes."""

        self.settings.setValue("remoteMode", str(self.remoteMode))
        self.settings.setValue("remoteIp", self.host)
        self.settings.setValue("remotePort", self.port)
        self.settings.setValue("cannoloDir", self.cannoloDir)
        self.settingsDialog.close()
        # self.settings.setValue("cannoloDir", self.cannoloLineEdit.text())
        # self.settings.setValue("theme", self.themeSelector.currentText())
        # self.client.stop(self.remoteMode)


class LocalServer(QThread):
    update = pyqtSignal(str, str, name="update")

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
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
        app = QApplication(sys.argv)
        window = PinoloMainWindow(app)
        app.exec_()

    except KeyboardInterrupt:
        print("KeyboardInterrupt")

    except BaseException:
        print(traceback.print_exc(file=sys.stdout))


if __name__ == "__main__":
    main()
