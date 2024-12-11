import os.path
from PyQt5.QtCore import QSettings, QSize, Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QFileDialog,
    QCompleter,
)
from utilities import warning_dialog
from constants import *
from ui.NetworkSettingsDialog import Ui_NetworkSettingsDialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pinolo import PinoloMainWindow


class NetworkSettings(QDialog, Ui_NetworkSettingsDialog):
    found_image = pyqtSignal(str)
    close_signal = pyqtSignal(QDialog)
    update_configuration = pyqtSignal()

    def __init__(self, parent: "PinoloMainWindow"):
        super(NetworkSettings, self).__init__(parent)
        self.setupUi(self)

        self.parent = parent
        self.settings = QSettings()
        self.asdGif = AsdGif(self)

        self.host = None
        self.port = None
        self.current_config_key = None
        self.images_directory = None
        self.default_image = None
        self.server_mode = None

        self.setup()

    def setup(self):
        self.get_settings()
        self.init_buttons()
        self.init_connection_settings()
        self.init_system_image_settings()

        self.found_image.connect(self.set_default_image_path)

    def init_buttons(self):
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.cancel)
        self.deleteConfigButton.clicked.connect(self.delete_config)
        self.connectButton.clicked.connect(self.connect)
        self.findButton.clicked.connect(self.find_image)

    def init_connection_settings(self):
        # set combo box
        if self.server_mode == LOCAL_MODE:
            self.serverModeComboBox.setCurrentIndex(0)
        else:
            self.serverModeComboBox.setCurrentIndex(1)
        self.serverModeComboBox.currentTextChanged.connect(self.update_line_edits)

        # set server ip line edits
        if self.server_mode == LOCAL_MODE:
            self.serverIpLineEdit.setReadOnly(True)
            self.serverPortLineEdit.setReadOnly(True)

        if self.host is None:
            self.serverIpLineEdit.setText(LOCAL_IP)
        else:
            self.serverIpLineEdit.setText(self.host)
        self.load_completer()

        # set server port line edits
        if self.port is None:
            self.serverPortLineEdit.setText(str(DEFAULT_PORT))
        else:
            self.serverPortLineEdit.setText(self.port)

        self.init_system_image_settings()

    def init_system_image_settings(self):
        # set images directory line edit
        self.imagesDirectoryLineEdit.setText(self.images_directory)
        self.imagesDirectoryLineEdit.textChanged.connect(self.defaultImageLineEdit.clear)
        # set default image line edit
        self.defaultImageLineEdit.setText(self.default_image)

    def get_settings(self):
        # get current server mode
        self.server_mode = self.settings.value(CURRENT_SERVER_MODE)
        if self.server_mode is None:
            self.server_mode = LOCAL_MODE

        # get current configuration
        self.current_config_key = self.settings.value(CURRENT_SERVER_CONFIG_KEY)

        # get current host and port
        self.settings.beginGroup(QSETTINGS_IP_GROUP)
        if self.current_config_key is None:
            self.host, self.port = (LOCAL_IP, str(DEFAULT_PORT))
        else:
            self.host, self.port, self.images_directory, self.default_image = self.settings.value(self.current_config_key)
        self.settings.endGroup()

        # get disk image settings
        # self.images_directory = self.settings.value(CURRENT_SERVER_IMAGES_DIRECTORY)
        # self.default_image = self.settings.value(CURRENT_SERVER_DEFAULT_IMAGE)
        if self.default_image is not None:
            self.default_image = os.path.basename(self.default_image)

    def update_line_edits(self):
        self.server_mode = self.serverModeComboBox.currentText()
        if self.server_mode == LOCAL_MODE:
            self.serverIpLineEdit.setReadOnly(True)
            self.serverPortLineEdit.setReadOnly(True)
        else:
            self.serverIpLineEdit.setReadOnly(False)
            self.serverPortLineEdit.setReadOnly(False)

    def save(self):
        self.save_configuration()
        self.close_signal.emit(self)
        self.accept()

    def save_configuration(self):
        self.server_mode = self.serverModeComboBox.currentText()
        self.host = self.serverIpLineEdit.text()
        self.port = self.serverPortLineEdit.text()
        self.images_directory = self.imagesDirectoryLineEdit.text()
        self.default_image = self.defaultImageLineEdit.text()
        self.settings.setValue(CURRENT_SERVER_MODE, self.server_mode)
        if self.server_mode == REMOTE_MODE:
            self.settings.beginGroup(QSETTINGS_IP_GROUP)
            for key in self.settings.childKeys():
                config = self.settings.value(key)  # [ip, port, ]

                if self.host in config:
                    self.settings.setValue(key, [self.host, self.port, self.images_directory, self.default_image])
                    self.settings.endGroup()
                    self.settings.setValue(CURRENT_SERVER_CONFIG_KEY, key)  # save current configuration key
                    break
            else:
                key = str(len(self.settings.childKeys()) + 1)
                self.settings.setValue(key, [self.host, self.port, self.images_directory, self.default_image])
                self.settings.endGroup()
                self.settings.setValue(CURRENT_SERVER_CONFIG_KEY, key)  # save current configuration key
        else:
            self.settings.setValue(LOCAL_IMAGES_DIRECTORY, self.images_directory)
            self.settings.setValue(LOCAL_DEFAULT_IMAGE, self.default_image)

        self.update_configuration.emit()

    def cancel(self):
        self.close_signal.emit(self)
        self.reject()

    def delete_config(self):
        ip = self.serverIpLineEdit.text()

        self.settings.beginGroup(QSETTINGS_IP_GROUP)
        for key in self.settings.childKeys():
            config = self.settings.value(key)  # [ip, port]
            if ip in config:
                message = f"Do you want to delete this configuration?\n{config[0]}:{config[1]}"
                if warning_dialog(message, dialog_type="yes_no") == QMessageBox.Yes:
                    self.settings.remove(key)
                    self.serverIpLineEdit.clear()
                    self.serverPortLineEdit.clear()
                    break
        self.settings.endGroup()
        self.load_completer()

    def load_completer(self):
        self.settings.beginGroup(QSETTINGS_IP_GROUP)
        suggestions = [self.settings.value(key)[0] for key in self.settings.childKeys()]
        self.settings.endGroup()
        completer = QCompleter(suggestions)
        completer.setCaseSensitivity(False)
        completer.activated.connect(self.autocomplete_port)
        self.serverIpLineEdit.setCompleter(completer)

    def autocomplete_port(self, completion):
        # index = model.stringList().index(completion) if completion in model.stringList else -1
        self.settings.beginGroup(QSETTINGS_IP_GROUP)
        for key in self.settings.childKeys():
            if completion in self.settings.value(key):
                self.serverPortLineEdit.setText(self.settings.value(key)[1])
        self.settings.endGroup()

    def find_image(self):
        """
        Opens a dialog to select a system image.
        If in remote mode, it connects to the server and lets the user choose an image from the server's image directory.
        If in local mode, it opens a file dialog to select an image from the local filesystem.
        """

        if self.serverModeComboBox.currentText() == REMOTE_MODE:
            connection = self.parent.connection_factory.protocol_instance
            requested_connection = False
            if not connection:
                warning_dialog("No connection. Connect to the server and retry.", "ok")
                return
            image_directory = self.imagesDirectoryLineEdit.text()
            if image_directory == "":
                warning_dialog("The path for the default system image is empty. Set it, plz.", dialog_type="ok")
                return

            if image_directory[-1] != "/":
                image_directory += "/"
                self.imagesDirectoryLineEdit.setText(image_directory)

            self.parent.select_image_requested.emit(image_directory, requested_connection)
            # if self.parent.select_system_dialog:
            #     self.parent.select_system_dialog.close()
            # self.parent.select_system_dialog = SelectSystemDialog(self, False, image_path)
        else:
            dialog = QFileDialog()
            # directory = dialog.getExistingDirectory(self, "Open Directory", "/home", QFileDialog.ShowDirsOnly)
            # directory = dialog.getExistingDirectory(self, "Open Directory", "/home")
            path = dialog.getOpenFileName(self, "Select new default image", "/home")[0]
            self.defaultImageLineEdit.setText(path)

    def set_default_image_path(self, path: str):
        self.defaultImageLineEdit.setText(os.path.basename(path))

    def connect(self):
        dialog = warning_dialog("Do you want to save the current settings and connect to the server?", "yes_no")
        if dialog == QMessageBox.No:
            return
        self.save_configuration()
        self.parent.connect_to_server()

    def closeEvent(self, a0):
        self.cancel()


class AsdGif(QMovie):
    def __init__(self, parent: NetworkSettings):
        super(AsdGif, self).__init__(parent)

        self.gif_path = PATH["ASD"]
        self.parent = parent

        self.setup()

    def setup(self):
        self.setFileName(self.gif_path)
        self.setScaledSize(QSize().scaled(self.parent.asdLabel.width(), self.parent.asdLabel.height(), Qt.KeepAspectRatio))
        self.start()
        self.parent.asdLabel.setMovie(self)
