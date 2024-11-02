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
from dialogs.SelectSystem import SelectSystemDialog

if TYPE_CHECKING:
    from pinolo import PinoloMainWindow


class NetworkSettings(QDialog, Ui_NetworkSettingsDialog):
    found_image = pyqtSignal(str)

    def __init__(self, parent: "PinoloMainWindow"):
        super(NetworkSettings, self).__init__()
        self.setupUi(self)

        self.parent = parent
        self.settings = QSettings()
        self.asdGif = AsdGif(self)

        self.setup()

    def setup(self):
        self.init_server_mode()
        self.init_buttons()
        self.init_line_edits()

        self.found_image.connect(self.set_default_image_path)

    def init_server_mode(self):
        server_mode = self.settings.value(SERVER_MODE)
        if server_mode is None:
            self.serverModeComboBox.setCurrentIndex(0)
            return
        self.serverModeComboBox.setCurrentText(server_mode)

    def init_buttons(self):
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.cancel)
        self.deleteConfigButton.clicked.connect(self.delete_config)
        self.findButton.clicked.connect(self.find_image)

    def init_line_edits(self):
        host = self.settings.value(SERVER_IP)
        port = self.settings.value(SERVER_PORT)
        images_directory = self.settings.value(SERVER_IMAGES_DIRECTORY)
        default_image = self.settings.value(SERVER_DEFAULT_IMAGE)

        if default_image is not None:
            default_image = os.path.basename(default_image)

        # server ip
        if host is None:
            self.serverIpLineEdit.setText(DEFAULT_IP)
        else:
            self.serverIpLineEdit.setText(host)
        self.load_completer()

        # server port
        if port is None:
            self.serverPortLineEdit.setText(str(DEFAULT_PORT))
        else:
            self.serverPortLineEdit.setText(port)

        # images directory
        self.imagesDirectoryLineEdit.setText(images_directory)
        self.imagesDirectoryLineEdit.textChanged.connect(self.defaultImageLineEdit.clear)

        # default image
        self.defaultImageLineEdit.setText(default_image)

    def save(self):
        self.save_config()

        server_mode = self.serverModeComboBox.currentText()
        host = self.serverIpLineEdit.text()
        port = self.serverPortLineEdit.text()
        images_directory = self.imagesDirectoryLineEdit.text()
        default_image = self.defaultImageLineEdit.text()

        self.settings.setValue(SERVER_MODE, server_mode)
        self.settings.setValue(SERVER_IP, host)
        self.settings.setValue(SERVER_PORT, port)
        self.settings.setValue(SERVER_IMAGES_DIRECTORY, images_directory)
        self.settings.setValue(SERVER_DEFAULT_IMAGE, default_image)

        self.parent.host = host
        self.parent.port = int(port)
        self.parent.default_image = default_image

        self.close()

    def save_config(self):
        """This function saves the active host and port configuration in the qt settings
        file, showing them in the recent ip list."""

        ip = self.serverIpLineEdit.text()
        port = self.serverPortLineEdit.text()

        self.settings.beginGroup(QSETTINGS_IP_GROUP)
        for key in self.settings.childKeys():
            config = self.settings.value(key)  # [ip, port]
            if ip in config:
                message = "Do you want to overwrite the old configuration?"
                if warning_dialog(message, dialog_type="yes_no") == QMessageBox.No:
                    self.settings.endGroup()
                    return
                else:
                    self.settings.setValue(key, [ip, port])
                    self.settings.endGroup()
                    return

        self.settings.setValue(str(len(self.settings.childKeys()) + 1), [ip, port])
        self.settings.endGroup()

        self.load_completer()

    def cancel(self):
        self.setup()
        self.close()

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
        This function opens a different dialog if
        the user is in local or remote mode to search for a cannolo image.
        """

        if self.serverModeComboBox.currentText() == REMOTE_MODE:
            image_directory = self.imagesDirectoryLineEdit.text()
            if image_directory == "":
                warning_dialog(
                    "The path for the default system image is empty. Set it, plz.",
                    dialog_type="ok"
                )
                return

            if image_directory[-1] != "/":
                image_directory += "/"
                self.imagesDirectoryLineEdit.setText(image_directory)

            self.parent.select_image_requested.emit(image_directory)
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
        self.setScaledSize(
            QSize().scaled(
                self.parent.asdLabel.width(),
                self.parent.asdLabel.height(),
                Qt.KeepAspectRatio
            )
        )
        self.start()
        self.parent.asdLabel.setMovie(self)