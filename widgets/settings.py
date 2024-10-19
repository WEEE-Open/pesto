from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QSettings, QSize, Qt
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QDialog, QRadioButton, QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox, QFileDialog
from client import ReactorThread
from utilities import critical_dialog, warning_dialog
from variables import *


class SettingsDialog(QDialog):
    update = pyqtSignal(str, int, bool, str, name="update_settings")

    def __init__(self, host: str, port: int, remoteMode: bool, cannoloDir: str, settings: QSettings, client: ReactorThread):
        super(SettingsDialog, self).__init__()
        uic.loadUi(PATH["SETTINGS_UI"], self)
        self.host = host
        self.port = port
        self.remoteMode = remoteMode
        self.cannoloDir = cannoloDir
        self.settings = settings
        self.client = client

        """ Defining widgets """
        self.localRadioBtn = self.findChild(QRadioButton, "localRadioBtn")
        self.remoteRadioBtn = self.findChild(QRadioButton, "remoteRadioBtn")
        self.ipLineEdit = self.findChild(QLineEdit, "ipLineEdit")
        self.portLineEdit = self.findChild(QLineEdit, "portLineEdit")
        self.restoreButton = self.findChild(QPushButton, "restoreButton")
        self.removeButton = self.findChild(QPushButton, "removeButton")
        self.defaultButton = self.findChild(QPushButton, "defaultButton")
        self.saveConfigButton = self.findChild(QPushButton, "saveConfigButton")
        self.ipList = self.findChild(QListWidget, "ipList")
        self.findButton = self.findChild(QPushButton, "findButton")
        self.cannoloLabel = self.findChild(QLabel, "cannoloLabel")
        self.cannoloLineEdit = self.findChild(QLineEdit, "cannoloLineEdit")
        self.cancelButton = self.findChild(QPushButton, "cancelButton")
        self.saveButton = self.findChild(QPushButton, "saveButton")

        """ Defining widgets functions """
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.cancel)
        self.restoreButton.clicked.connect(self.restore_config)
        self.defaultButton.clicked.connect(self.default_config)
        self.removeButton.clicked.connect(self.remove_config)
        self.saveConfigButton.clicked.connect(self.save_config)
        self.findButton.clicked.connect(self.find_image)

        # radio buttons
        if not self.remoteMode:
            self.localRadioBtn.setChecked(True)
        else:
            self.remoteRadioBtn.setChecked(True)
        self.localRadioBtn.clicked.connect(self.set_remote_mode)
        self.remoteRadioBtn.clicked.connect(self.set_remote_mode)

        """ Fill parameters in widgets """
        # host input
        self.ipLineEdit.setText(self.host)

        # port input
        if self.port is not None:
            self.portLineEdit.setText(str(self.port))

        # cannolo text
        self.cannoloLineEdit.setText(self.cannoloDir)
        if self.remoteMode:
            self.cannoloLineEdit.setReadOnly(False)

        """ Defining extremely important asd gif """
        self.asdlabel = self.findChild(QLabel, "asdLabel")
        self.asdGif = QMovie(PATH["ASD"])
        self.asdGif.setScaledSize(QSize().scaled(self.asdlabel.width(), self.asdlabel.height(), Qt.KeepAspectRatio))

        # configuration list
        for key in self.settings.childKeys():
            if "saved" in key:
                values = self.settings.value(key)
                self.ipList.addItem(values[0])
        self.ipList.clicked.connect(self.load_config)

        self.asdGif.start()
        self.asdlabel.setMovie(self.asdGif)

        self.set_remote_mode()

    def set_remote_mode(self):
        """This function set all the parameters related to the client-server
        communications and other UI-related behaviours."""

        if self.localRadioBtn.isChecked():
            self.remoteMode = False
            self.settings.setValue("latestHost", self.host)
            self.settings.setValue("latestPort", self.port)
            self.host = "127.0.0.1"
            self.port = 1030
            self.ipLineEdit.setText(self.host)
            self.portLineEdit.setText(str(self.port))
            self.ipLineEdit.setReadOnly(True)
            self.portLineEdit.setReadOnly(True)
            self.cannoloLineEdit.setReadOnly(True)
            self.cannoloLabel.setText("")
        elif self.remoteRadioBtn.isChecked():
            if not self.remoteMode:
                try:
                    self.host = self.settings.value("latestHost")
                    self.port = int(self.settings.value("latestPort"))
                except:
                    pass
            self.remoteMode = True
            self.ipLineEdit.setReadOnly(False)
            self.ipLineEdit.setText(self.host)
            self.portLineEdit.setReadOnly(False)
            self.portLineEdit.setText(str(self.port))
            self.saveButton.setEnabled(True)
            self.cannoloLineEdit.setReadOnly(False)
            self.cannoloLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")

    def save(self):
        self.host = self.ipLineEdit.text()
        self.port = int(self.portLineEdit.text())
        self.cannoloDir = self.cannoloLineEdit.text()
        self.hide()
        self.update.emit(self.host, self.port, self.remoteMode, self.cannoloDir)

    def cancel(self):
        self.restore_config()
        self.hide()

    def restore_config(self):
        """This function delete all the edits made in the host and port input
        in the settings tab."""

        self.ipLineEdit.setText(self.host)
        self.portLineEdit.setText(str(self.port))

    def default_config(self):
        """This function removes all the data from the qt settings file.
        Use with caution."""

        message = "Do you want to restore all settings to default?\nThis action is unrevocable."
        if critical_dialog(message, dialog_type="yes_no") == QMessageBox.Yes:
            self.settings.clear()
            self.ipList.clear()

    def remove_config(self):
        """This function removes the selected configuration in the recent
        ip list in the settings tab."""
        try:
            ip = self.ipList.currentItem().text()
        except:
            return
        message = "Do you want to remove the selected configuration?"
        if warning_dialog(message, dialog_type="yes_no") == QMessageBox.Yes:
            for key in self.settings.childKeys():
                if ip in key:
                    self.ipList.takeItem(self.ipList.row(self.ipList.currentItem()))
                    self.settings.remove(key)

    def save_config(self):
        """This function saves the active host and port configuration in the qt settings
        file, showing them in the recent ip list."""

        ip = self.ipLineEdit.text()
        port = self.portLineEdit.text()
        if self.ipList.findItems(ip, Qt.MatchExactly):
            message = "Do you want to overwrite the old configuration?"
            if warning_dialog(message, dialog_type="yes_no") == QMessageBox.Yes:
                self.settings.setValue("saved-" + ip, [ip, port])
        else:
            self.ipList.addItem(ip)
            self.settings.setValue("saved-" + ip, [ip, port])

    def set_default_cannolo(self, directory: str):
        """This function set the default cannolo path in the settings tab."""
        self.cannoloLineEdit.setText(directory)

    def find_image(self):
        """This function opens a different dialog, depending if
        the user is in local or remote mode, to search for a cannolo image."""

        # noinspection PyBroadException
        try:
            if self.remoteMode:
                directory = self.cannoloLineEdit.text()
                splitted_dir = directory.rsplit("/", 1)
                if len(splitted_dir[1].split(".")) > 1:
                    self.client.send("list_iso " + directory.rsplit("/", 1)[0])
                else:
                    if directory[-1] != "/":
                        directory += "/"
                    self.client.send("list_iso " + directory)
            else:
                dialog = QFileDialog()
                directory = dialog.getExistingDirectory(self, "Open Directory", "/home", QFileDialog.ShowDirsOnly)
                self.cannoloLineEdit.setText(directory)

        except BaseException as ex:
            print(f"GUI: Error in smart function [{ex}]")

    def load_config(self):
        """This function loads the selected configuration in the recent ip
        list in the settings tab."""

        ip = self.ipList.currentItem().text()
        for key in self.settings.childKeys():
            if ip in key:
                values = self.settings.value(key)
                port = values[1]
                self.ipLineEdit.setText(ip)
                self.portLineEdit.setText(port)
