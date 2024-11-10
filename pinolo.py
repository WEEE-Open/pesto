#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""
import json
import os.path
import sys
import time
import humanize
from client import ConnectionFactory

from utilities import *
from ui.PinoloMainWindow import Ui_MainWindow
from dialogs.NetworkSettings import NetworkSettings
from dialogs.SmartDialog import SmartDialog
from dialogs.SelectSystem import SelectSystemDialog
from typing import Union
from dotenv import load_dotenv
from PyQt5.QtGui import QIcon, QDesktopServices, QPixmap, QCloseEvent
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QThread, QUrl, pyqtSlot, QCoreApplication, \
    QAbstractTableModel, QModelIndex, QPoint
from PyQt5.QtWidgets import (
    QTableWidgetItem,
    QTableWidget,
    QMessageBox,
    QMainWindow,
    QProgressBar,
    QInputDialog,
    QLineEdit,
    QDialog,
    QStyledItemDelegate,
    QTableView
)
from constants import *
from typing import List

# Linter settings
from twisted.internet.interfaces import IReactorTCP
reactor: IReactorTCP


class PinoloMainWindow(QMainWindow, Ui_MainWindow):
    select_image_requested = pyqtSignal(str, bool)

    def __init__(self):
        super(PinoloMainWindow, self).__init__()
        self.setupUi(self)

        self.host = None
        self.port = None
        self.current_config_key = None
        self.images_directory = None
        self.default_image = None
        self.server_mode = None

        self.drivesTableViewModel = DrivesTableModel(self.drivesTableView)
        self.queueTableViewModel = QueueTableModel(self.queueTableView)

        # TO BE FIXED THINGS
        self.active_theme = None

        self.current_mountpoints = dict()
        self.smart_results = {}

        self.settings = QSettings()

        self.connection_factory = ConnectionFactory(self)
        self.connection_factory.data_received.connect(self.gui_update)

        # Handlers
        self.dialogs = []
        self.select_system_dialog: SelectSystemDialog = None

        # Set icons
        if QIcon.hasThemeIcon("data-warning"):
            self._mount_warning_icon = QIcon.fromTheme("data-warning")
        else:
            self._mount_warning_icon = QIcon.fromTheme("dialog-warning")
        self._progress_icon = QIcon(QPixmap(PATH["PROGRESS"]))

        # initialize attributes with latest session parameters (host, port and default system path)
        self.load_configuration()

        # Setup ui functionalities
        self.setup()

        # Start client
        self.connect_to_server()

    def setup(self):
        # Drives table
        self.drivesTableView.setModel(self.drivesTableViewModel)
        delegate = StatusIconDelegate(self.drivesTableView)
        self.drivesTableView.setItemDelegateForColumn(DRIVES_TABLE_STATUS, delegate)
        self.drivesTableView.addActions([self.actionSleep, self.actionUmount, self.actionShow_SMART_data, self.actionUpload_to_Tarallo])
        self.actionSleep.triggered.connect(self.sleep)
        self.actionUmount.triggered.connect(self.umount)
        self.actionShow_SMART_data.triggered.connect(self.show_smart_data)
        self.actionUpload_to_Tarallo.triggered.connect(self.upload_to_tarallo)

        # Queue table
        self.queueTableView.setModel(self.queueTableViewModel)
        delegate = ProgressBarDelegate(self.queueTableView)
        self.queueTableView.setItemDelegateForColumn(QUEUE_TABLE_PROGRESS, delegate)
        delegate = StatusIconDelegate(self.queueTableView)
        self.queueTableView.setItemDelegateForColumn(QUEUE_TABLE_STATUS, delegate)
        self.queueTableView.addActions(
            [self.actionStop, self.actionRemove, self.actionRemove_All, self.actionRemove_completed, self.actionRemove_Queued]
        )
        self.actionStop.triggered.connect(self.queue_stop)
        self.actionRemove.triggered.connect(self.queue_remove)
        self.actionRemove_All.triggered.connect(self.queue_clear)
        self.actionRemove_completed.triggered.connect(self.queue_clear_completed)
        self.actionRemove_Queued.triggered.connect(self.queue_clear_queued)

        # Buttons
        self.standardProcedureButton.clicked.connect(self.standard_procedure)
        self.eraseButton.clicked.connect(self.erase)
        self.smartCheckButton.clicked.connect(self.smart_check)
        self.loadSystemButton.clicked.connect(self.load_system)
        self.refreshButton.clicked.connect(self.refresh)

        # Menu bar
        self.actionNetworkSettings.triggered.connect(self.open_network_settings)
        self.actionSourceCode.triggered.connect(self.open_source_code)
        self.actionAboutUs.triggered.connect(self.open_website)
        self.actionVersion.triggered.connect(self.show_version)

        self.select_image_requested.connect(self.set_default_image)

    # NETWORKING
    def open_network_settings(self):
        network_settings = NetworkSettings(self)
        network_settings.close_signal.connect(self._remove_dialog_handler)
        network_settings.update_configuration.connect(self.load_configuration)
        network_settings.show()
        self.dialogs.append(network_settings)

    def connect_to_server(self):
        """This method must be called in __init__ function of Ui class
        to initialize pinolo session"""

        # Check if the host and port field are set
        if self.host is None and self.port is None:
            message = "The host and port combination is not set.\nPlease visit the settings section."
            warning_dialog(message, dialog_type="ok")

        # Connect to server and connect signal to callback
        if self.server_mode == REMOTE_MODE:
            reactor.connectTCP(self.host, int(self.port), self.connection_factory, CLIENT_TIMEOUT)
        else:
            reactor.connectTCP(LOCAL_IP, int(DEFAULT_PORT), self.connection_factory, CLIENT_TIMEOUT)

    def send_command(self, msg: str):
        if msg and self.connection_factory.protocol_instance:
            self.connection_factory.protocol_instance.send_msg(msg)
        else:
            print("PINOLO: No connection. Cannot send message.")

    # SETTINGS
    def load_configuration(self):
        """This function try to set the remote configuration used in the last
        pinolo session"""

        # get current server mode
        self.server_mode = self.settings.value(CURRENT_SERVER_MODE)

        # REMOTE MODE CONFIG
        if self.server_mode == REMOTE_MODE:
            # get current configuration
            self.current_config_key = self.settings.value(CURRENT_SERVER_CONFIG_KEY)

            # get current host and port
            self.settings.beginGroup(QSETTINGS_IP_GROUP)
            if self.current_config_key is None:
                self.host, self.port = (LOCAL_IP, str(DEFAULT_PORT))
            else:
                self.host, self.port, self.images_directory, self.default_image = self.settings.value(self.current_config_key)
            self.settings.endGroup()

        # LOCAL MODE CONFIG
        else:
            self.current_config_key = None
            self.host = LOCAL_IP
            self.port = DEFAULT_PORT
            self.images_directory = self.settings.value(LOCAL_IMAGES_DIRECTORY)
            self.default_image = self.settings.value(LOCAL_DEFAULT_IMAGE)

        if self.default_image is not None:
            self.default_image = os.path.basename(self.default_image)

    # MENU BAR ACTIONS
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

    # QUEUE TABLE ACTIONS
    def queue_stop(self):
        """This function set the "stop" button behaviour on the queue table
        context menu."""
        dialog = warning_dialog(
            "Do you want to stop the selected processes?",
            "yes_no"
        )
        if dialog == QMessageBox.No:
            return

        rows = self.queueTableView.selectionModel().selectedRows()
        for index in rows:
            pid = self.queueTableViewModel.get_pid(index)
            self.send_command(f"stop {pid}")

    def queue_remove(self):
        """This function set the "remove" button behaviour on the queue table
        context menu."""
        dialog = warning_dialog(
            "With this action you will also stop the selected processes.\nDo you want to proceed?",
            "yes_no"
        )
        if dialog == QMessageBox.No:
            return

        rows = self.queueTableView.selectionModel().selectedRows()
        for index in rows:
            pid = self.queueTableViewModel.get_pid(index)
            self.send_command(f'remove {pid}')
        self.queueTableViewModel.remove_row(rows)

    def queue_clear(self):
        """This function set the "remove all" button behaviour on the queue table
        context menu."""

        self.queueTableViewModel.remove_all()
        self.send_command("remove_all")

    def queue_clear_completed(self):
        """This function set the "remove completed" button behaviour on the queue table
        context menu."""

        self.queueTableViewModel.remove_completed()
        self.send_command("remove_completed")

    def queue_clear_queued(self):
        """This function set the "remove completed" button behaviour on the queue table
        context menu."""

        self.queueTableViewModel.remove_queued()
        self.send_command("remove_queued")

    # DISK TABLE ACTIONS
    def upload_to_tarallo(self, standard_procedure: bool = False):
        # TODO: check if it's really working

        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        for drive in drives:
            tarallo_id = self.get_tarallo_id(drive)
            if not standard_procedure:
                if tarallo_id != "":
                    warning_dialog(
                        f"The drive {drive} already has a TARALLO id.",
                        dialog_type="ok"
                    )
                    continue
                dialog = warning_dialog(
                    f"Do you want to create the disk item for {drive} in TARALLO?",
                    dialog_type="yes_no"
                )
                if dialog == QMessageBox.No:
                    continue

            else:
                if tarallo_id != "":
                    continue

            location, ok = tarallo_location_dialog(f"Please, set the Tarallo location of drive {drive}.\n"
                                                   f"Leave blank to avoid upload to Tarallo")

            # If no location is provided or cancel is selected, stop the operation
            if not ok or location is None or location == "":
                continue

            self.send_command(f"queued_upload_to_tarallo {drive} {location}")

    def sleep(self):
        """This function send to the server a queued_sleep command.
        If "std" is True it will skip the "no drive selected" check."""

        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        for drive in drives:
            drive = drive
            self.send_command("queued_sleep " + drive)

    def select_image(self, image_path: str, ):
        self.select_system_dialog = SelectSystemDialog(self)
        self.send_command(f"list_iso {image_path.rstrip('/')}")
        if self.select_system_dialog.exec_() == QDialog.Accepted:
            selected_image = self.select_system_dialog.get_selected_image()
            return image_path + selected_image
        return None

    def set_default_image(self, image_path: str):
        image = self.select_image(image_path)

        if image is None:
            return

        for dialog in self.dialogs:
            if isinstance(dialog, NetworkSettings):
                dialog.set_default_image_path(image)

    def umount(self):
        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        drives_as_text = " and ".join(drives)
        mountpoints = []
        for drive in drives:
            try:
                for mp in self.current_mountpoints[drive]:
                    mountpoints.append(mp)
            except IndexError:
                pass
            except KeyError:
                pass

        if len(mountpoints) <= 0:
            return

        mountpoints_as_text = "\n".join(sorted(mountpoints))

        message = f"Are you really sure you want to unmount all partitions of {drives_as_text}?\n"
        # I love reinventing gettext and solving problems that have been solved since 1995
        # (maybe we should use the real gettext at some point, even if we don't have translations)
        if len(drives) <= 1:
            message += "It has the following mountpoints:\n"
        else:
            message += "They have the following mountpoints:\n"
        message += mountpoints_as_text
        message += "\nBe careful not to unmount and erase something important."

        dialog = warning_dialog(
            message,
            "yes_no",
        )

        if dialog == QMessageBox.Yes:
            for drive in drives:
                self.send_command("queued_umount " + drive)

    def get_multiple_drive_selection(self):
        """This method returns a list with the names of the selected drives on disk_table"""
        drives = []
        selected_rows = self.drivesTableView.selectionModel().selectedRows()

        if len(selected_rows) == 0:
            warning_dialog(
                "There are no selected drives.",
                dialog_type="ok"
            )
            return None

        for row in selected_rows:
            drives.append(row.data())

        return drives

    def get_tarallo_id(self, drive: str):
        for row in range(self.drivesTableView.rowCount()):
            item = self.drivesTableView.item(row, DRIVES_TABLE_NAME)
            if item.text() == drive:
                return self.drivesTableView.item(row, DRIVES_TABLE_TARALLO_ID).text()
        return None

    def show_smart_data(self):
        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        for drive in drives:
            # TODO: check if this works properly
            if drive in self.smart_results:
                smart_dialog = SmartDialog(self, drive, self.smart_results[drive])
                smart_dialog.close_signal.connect(self._remove_dialog_handler)
                self.dialogs.append(smart_dialog)

    # BUTTONS CALLBACKS
    def refresh(self):
        """This function read the host and port inputs in the settings
        tab and try to reconnect to the server, refreshing the disk list."""
        self._clear_tables()
        if self.connection_factory.protocol_instance:
            self.connection_factory.protocol_instance.disconnect()
        self.connect_to_server()

    def standard_procedure(self):
        """This function send to the server a sequence of commands:
        - queued_badblocks
        - queued_smartctl
        - queued_cannolo (if the cannolo flag on the dialog is checked)
        - queued_sleep
        """

        drives = self.get_multiple_drive_selection()

        if drives is None:
            return
        standard_procedure_dialog = warning_dialog(
            "Do you want to wipe all disk's data and load a fresh system image?",
            dialog_type="yes_no_chk"
        )

        if standard_procedure_dialog[0] == QMessageBox.No:
            return
        self.upload_to_tarallo(standard_procedure=True)
        self.erase(standard_procedure=True)
        self.smart_check()
        if standard_procedure_dialog[1]:
            self.load_system(standard_procedure=True)

    def erase(self, standard_procedure=False):
        """This function send to the server a queued_badblocks command.
        If "std" is True it will skip the confirm dialog."""

        # noinspection PyBroadException
        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        if not standard_procedure:
            message = f"Do you want to wipe all selected disks' data?\n"
            if critical_dialog(message, dialog_type="yes_no") != QMessageBox.Yes:
                return
        for drive in drives:
            self.send_command("queued_badblocks " + drive)

    def smart_check(self):
        """This function send to the server a queued_smartctl command.
        If "std" is True it will skip the "no drive selected" check."""

        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        for drive in drives:
            self.send_command("queued_smartctl " + drive)

    def load_system(self, standard_procedure=False):
        """This function send to the server a queued_cannolo command.
        If "std" is True it will skip the cannolo dialog."""
        drives = self.get_multiple_drive_selection()

        if drives is None:
            return

        if self.images_directory == "":
            critical_dialog("There is no default image set in Pinolo settings.", dialog_type="ok")
            return

        if standard_procedure:
            image = self.images_directory + self.default_image
        else:
            image = self.select_image(self.images_directory)

        if image is None:
            return

        for drive in drives:
            print(f"GUI: Sending cannolo to {drive} with {image}")
            self.send_command(f"queued_cannolo {drive} {image}")

    # INTERNAL METHODS
    def _set_disk_table_item(self, table: QTableWidget, row: int, drive: dict):
        table.setRowCount(row + 1)
        table.setItem(row, 0, QTableWidgetItem(drive["path"]))
        table.setItem(row, 1, QTableWidgetItem(drive["code"]))
        table.setItem(
            row,
            2,
            QTableWidgetItem(format_size(drive["size"], True, False)),
        )
        if drive["mountpoint"]:
            self.current_mountpoints[drive["path"]] = drive["mountpoint"]
            self._decorate_disk(table.item(row, 0), False)
        else:
            if drive["path"] in self.current_mountpoints:
                del self.current_mountpoints[drive["path"]]

    def _clear_tables(self):
        self.drivesTableView.setRowCount(0)
        self.queueTableViewModel.clear()

    def _decorate_disk(self, item: QTableWidgetItem, something_in_progress: bool):
        if something_in_progress:
            item.setIcon(self._progress_icon)
            item.setToolTip(None)
        elif item.text() in self.current_mountpoints:
            item.setIcon(self._mount_warning_icon)
            item.setToolTip("Disk has critical mountpoints, some action are restricted.")
        else:
            item.setIcon(QIcon())
            item.setToolTip(None)

    def _send_sudo_password(self, password: str):
        # password = password.replace('\\', '\\\\').replace(" ", "\\ ")
        self.send_command(f"sudo_password {password}")

    def _check_disk_usage(self):
        #TODO: broken
        disks_rows = self.drivesTableView.rowCount()
        queue_rows = self.queueTableViewModel.rowCount()

        if queue_rows == 0:
            return

        # for disk_row in range(disks_rows):
        #     disk_id = self.drivesTableView.item(disk_row, DISK_TABLE_DRIVE).text()
        #     for queue_row in range(queue_rows):
        #         if disk_id != self.queueTableView.item(queue_row, QUEUE_TABLE_DRIVE).text():
        #             eta = self.queueTableView.item(queue_row, QUEUE_TABLE_ETA).text()
        #             if eta != "":

        if queue_rows > 0 and disks_rows > 0:
            for disk_row in range(disks_rows + 1):
                disk_label = self.drivesTableView.item(disk_row, 0)
                if disk_label is not None:
                    disk_label = disk_label.text()
                    for queue_row in range(queue_rows + 1):
                        queue_disk_label = self.queueTableView.item(queue_row, 2)
                        queue_progress = self.queueTableView.cellWidget(queue_row, 5)
                        if self.drivesTableView.item(disk_row, 0).text() in self.current_mountpoints:
                            continue
                        if queue_disk_label is not None and queue_progress is not None:
                            queue_disk_label = queue_disk_label.text()
                            queue_progress = queue_progress.findChild(QProgressBar).value()
                            if queue_disk_label == disk_label and queue_progress != (100 * PROGRESS_BAR_SCALE):
                                self._decorate_disk(self.drivesTableView.item(disk_row, 0), True)
                                break
                        if queue_row == queue_rows:
                            self._decorate_disk(self.drivesTableView.item(disk_row, 0), False)

    def _remove_dialog_handler(self, dialog: QDialog):
        self.dialogs.remove(dialog)

    @pyqtSlot(str, str)
    def gui_update(self, command: str, command_data: str):
        """
        This function gets all the server responses and update, if possible, the UI.

        Typical param str is:
            cmd [{param_1: 'text'}, {param_2: 'text'}, {param_3: 'text'}, ...]
        Possible cmd are:
            get_disks --> drives information for disks table
            queue_status --> Information about badblocks process

        """
        if len(command_data) > 0:
            try:
                command_data = json.loads(command_data)
                command_data: Union[dict, list]
            except json.decoder.JSONDecodeError:
                print(f"GUI: Ignored exception while parsing {command}, expected JSON but this isn't: {command_data}")

        match command:
            case "queue_status" | "get_queue":
                # if cmd == "queue_status":
                #     params = [params]
                if isinstance(command_data, dict):
                    command_data = [command_data]
                for data in command_data:
                    self.queueTableViewModel.update_table(data)

            case "queued_umount":
                self.send_msg("get_disks")

            case "get_disks":
                self.drivesTableViewModel.load_data(command_data)

            case "smartctl" | "queued_smartctl":
                # if params["status"] == "password_required":
                #     passwd, ok = QInputDialog.getText(self, "Input Password", "Enter server sudo password:", QLineEdit.Password)
                #     if ok:
                #         self.smart_check(False, passwd)
                #         self.queue_remove(params["pid"], params["disk"])
                #     return
                self.smart_results[command_data["disk"]] = {"output": command_data["output"], "status": command_data["status"]}

            case "connection_failed":
                self.statusbar.showMessage(f"⚠ Connection failed. Check settings and try to reconnect.")
                self._clear_tables()
                pass

            case "connection_lost":
                self.statusbar.showMessage(f"⚠ Connection lost.")
                self._clear_tables()

            case "connection_made":
                self.statusbar.showMessage(f"Connected to {command_data['host']}:{command_data['port']}")
                self.connection_factory.protocol_instance.send_msg("get_disks")
                self.connection_factory.protocol_instance.send_msg("get_queue")

            case "list_iso":
                self.select_system_dialog.load_images(command_data)

            case "error":
                message = f"{command_data['message']}"
                if "command" in command_data:
                    message += f":\n{command_data['command']}"
                critical_dialog(message, dialog_type="ok")

            case "error_that_can_be_manually_fixed":
                message = command_data["message"]
                warning_dialog(message, dialog_type="ok")

            case "sudo_password":
                passwd, ok = QInputDialog.getText(self, "Input Password", "Enter server sudo password:", QLineEdit.Password)
                if ok:
                    self._send_sudo_password(passwd)
                else:
                    warning_dialog(
                        "You did not enter the root password.\n" "Some commands may not work correctly.\n" "Refresh to insert the password.", dialog_type="ok"
                    )

        # self.check_disk_usage()

    def closeEvent(self, a0: QCloseEvent) -> None:
        """
        This function is called when the window is closed.
        It will save all the latest settings parameters into the QT settings file and
        terminate all the active audio processes.
        """
        if self.connection_factory.protocol_instance:
            self.connection_factory.protocol_instance.disconnect()
        QCoreApplication.instance().quit()


class Job:
    def __init__(self, command_data: dict):
        self.pid = command_data["id"]
        self.drive = command_data["target"]
        self.type = self._format_process_type(command_data["command"])
        self.status = self._parse_status(command_data)
        self.progress: float = command_data["percentage"]

        self.status_icon = None

        # Eta attributes
        self.eta = None
        self.start_time = time.time()

    def update(self, command_data: dict):
        self.status = self._parse_status(command_data)
        self.progress = command_data["percentage"]
        self._update_eta()

    def _update_eta(self):
        elapsed_time = time.time() - self.start_time
        if 0 < self.progress < 100:
            predicted_total_time = elapsed_time / (self.progress/100)
            eta = predicted_total_time - elapsed_time
            self.eta = time.strftime("%H:%M:%S", time.gmtime(eta))
        else:
            self.eta = None

    @staticmethod
    def _format_process_type(command: str):
        match command:
            case "queued_badblocks":
                return "Erase"
            case "queued_smartctl":
                return "Smart check"
            case "queued_cannolo":
                return "Load system"
            case "queued_upload_to_tarallo":
                return "Upload data"
            case _:
                return command

    @staticmethod
    def _parse_status(command_data: list):
        if command_data["stale"]:
            return "stale"
        elif command_data["stopped"]:
            return "stopped"
        elif command_data["error"]:
            return "error"
        elif command_data["finished"]:  # and not error
            return "finished"
        elif command_data["started"]:
            return "started"
        else:
            return "pending"


class QueueTableModel(QAbstractTableModel):
    def __init__(self, parent: QTableView):
        self.parent = parent
        super().__init__()
        self.jobs: List[Job] = []
        self.header_labels = [
            "Drive",
            "Process",
            "Status",
            "Eta",
            "Progress"
        ]

    def rowCount(self, parent = ...) -> int:
        return len(self.jobs)

    def columnCount(self, parent = ...) -> int:
        return len(self.header_labels)

    def headerData(self, section, orientation, role = ...):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]

    def data(self, index: QModelIndex, role = ...):
        # index: specific cell in the table

        match role:
            case Qt.DisplayRole:
                job = self.jobs[index.row()]
                attribute = self.header_labels[index.column()]
                match attribute:
                    case "Drive":
                        return job.drive
                    case "Process":
                        return job.type
                    case "Status":
                        return job.status
                    case "Eta":
                        return job.eta
                    case "Progress":
                        return job.progress

            case Qt.TextAlignmentRole:
                return Qt.AlignHCenter | Qt.AlignVCenter
            case Qt.ToolTipRole:
                job = self.jobs[index.row()]
                if index.column() == QUEUE_TABLE_STATUS:
                    return job.status
            case _:
                return None

    def update_table(self, command_data: dict):
        found_job_idx = self._check_pid(command_data["id"])

        # create row if job does not exist
        if found_job_idx is None:
            new_job = Job(command_data)
            self._insert_row(new_job)

        # update row if job exist
        else:
            job = self.jobs[found_job_idx]
            job.update(command_data)
            self._update_row(found_job_idx)

    def remove_completed(self):
        self.beginResetModel()
        for job in self.jobs[::-1]:
            if job.status == "finished":
                self.jobs.remove(job)
        self.endResetModel()

    def remove_all(self):
        self.beginResetModel()
        self.jobs.clear()
        self.endResetModel()

    def remove_queued(self):
        self.beginResetModel()
        for job in self.jobs[::-1]:
            if job.status == "pending":
                self.jobs.remove(job)
        self.endResetModel()

    def remove_row(self, rows: List[QModelIndex]):
        self.beginResetModel()
        for index in rows[::-1]:
            del self.jobs[index.row()]
        self.endResetModel()

    def get_pid(self, index: QModelIndex):
        row = index.row()
        return self.jobs[row].pid

    def _check_pid(self, pid: str):
        for idx, job in enumerate(self.jobs):
            if pid == job.pid:
                return idx
        return None

    def _update_row(self, row: int):
        first_cell = self.index(row, 0)
        last_cell = self.index(row, len(self.header_labels) - 1)
        self.dataChanged.emit(first_cell, last_cell)

    def _insert_row(self, new_job: Job):
        self.beginInsertRows(QModelIndex(), len(self.jobs), len(self.jobs))
        self.jobs.append(new_job)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self.jobs.clear()
        self.endResetModel()


class ProgressBarDelegate(QStyledItemDelegate):
    def __init__(self, parent = None):
        super(ProgressBarDelegate, self).__init__(parent)
        self.margin = 1

    def paint(self, painter, option, index):
        if index.column() == QUEUE_TABLE_PROGRESS:
            progress: float = index.data()
            if progress is None:
                progress = 0

            # Create a progress bar widget
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100*PROGRESS_BAR_SCALE)
            progress_bar.setValue(int(progress*PROGRESS_BAR_SCALE))

            # Render the progress bar inside the cell
            rect = option.rect.adjusted(self.margin, 0, -self.margin, 0)
            progress_bar_height = progress_bar.sizeHint().height()
            vertical_offset = (rect.height() - progress_bar_height) // 2
            centered_rect = rect.adjusted(0, vertical_offset, 0, -vertical_offset)

            progress_bar.resize(centered_rect.size())
            painter.save()
            painter.translate(option.rect.topLeft())
            progress_bar.render(painter, QPoint(0, vertical_offset))
            painter.restore()
        else:
            # Default rendering for other columns
            super(ProgressBarDelegate, self).paint(painter, option, index)


class StatusIconDelegate(QStyledItemDelegate):
    def __init__(self, parent = None):
        super(StatusIconDelegate, self).__init__(parent)
        self.icons = {
            "error": QIcon("assets/table/error.png"),
            "started": QIcon("assets/table/progress.png"),
            "pending": QIcon("assets/table/pending.png"),
            "stop": QIcon("assets/table/stop.png"),
            "finished": QIcon("assets/table/ok.png"),
            "warning": QIcon("assets/table/warning.png"),
        }
        self.margin = 2

    def paint(self, painter, option, index):
        if index.column() == QUEUE_TABLE_STATUS:
            status: str = index.data()
            if status in self.icons:
                icon: QIcon = self.icons[status]
                rect = option.rect.adjusted(self.margin, self.margin, -self.margin, -self.margin)
                icon.paint(painter, rect)
                return

        super().paint(painter, option, index)


class Drive:
    def __init__(self, drive: dict):
        self.name = drive["path"]
        self.mounted = True if drive["mountpoint"] else False
        self.status = None
        self.tarallo_id = drive["code"]
        self.size = drive["size"]


class DrivesTableModel(QAbstractTableModel):
    def __init__(self, parent: QTableView):
        super().__init__()
        self.parent = parent
        self.drives: List[Drive] = []
        self.header_labels = [
            "Drive",
            "Status",
            "Tarallo ID",
            "Size"
        ]

    def rowCount(self, parent = ...) -> int:
        return len(self.drives)

    def columnCount(self, parent = ...) -> int:
        return len(self.header_labels)

    def headerData(self, section, orientation, role = ...):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]

    def data(self, index: QModelIndex, role = ...):
        # index: specific cell in the table

        match role:
            case Qt.DisplayRole:
                drive = self.drives[index.row()]
                attribute = self.header_labels[index.column()]
                match attribute:
                    case "Drive":
                        return drive.name
                    case "Status":
                        return drive.status
                    case "Tarallo ID":
                        return drive.tarallo_id
                    case "Size":
                        return humanize.naturalsize(drive.size)

            case Qt.TextAlignmentRole:
                return Qt.AlignLeft | Qt.AlignVCenter
            case Qt.ToolTipRole:
                drive = self.drives[index.row()]
                if index.column() == DRIVES_TABLE_STATUS:
                    return drive.status
            case _:
                return None

    def load_data(self, drives: List[dict]):
        for drive in drives:
            self.beginInsertRows(QModelIndex(), len(self.drives), len(self.drives))
            self.drives.append(Drive(drive))
            self.endInsertRows()
        self._resize_columns()

    def _resize_columns(self):
        for column in range(3):
            self.parent.resizeColumnToContents(column)

    def clear(self):
        self.beginResetModel()
        self.drives.clear()
        self.endResetModel()


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


if __name__ == "__main__":
    try:
        load_dotenv(PATH["ENV"])

        # Create application
        app = QtWidgets.QApplication(sys.argv)
        app.setOrganizationName("WEEE-Open")
        app.setApplicationName("PESTO")

        # Integrate twisted event loop in pyqt loop
        import qt5reactor
        qt5reactor.install()
        from twisted.internet import reactor

        # Create main window
        window = PinoloMainWindow()
        window.show()

        # Run main loop
        reactor: IReactorTCP
        reactor.run()

    except KeyboardInterrupt:
        print("KeyboardInterrupt")
