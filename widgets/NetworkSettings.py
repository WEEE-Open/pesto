from PyQt5.QtCore import pyqtSignal, QSettings, QSize, Qt
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QFileDialog,
    QCompleter,
)
from utilities import warning_dialog
from constants import *
from ui.NetworkSettingsWidget import Ui_NetworkSettingsWidget
from typing import TYPE_CHECKING
from widgets.SelectSystem import SelectSystemDialog

if TYPE_CHECKING:
    from pinolo import PinoloMainWindow


class NetworkSettings(QDialog, Ui_NetworkSettingsWidget):
    update = pyqtSignal(str, int, bool, str, name="update_settings")

    def __init__(self, parent: "PinoloMainWindow"):
        super(NetworkSettings, self).__init__()
        self.setupUi(self)

        self.parent = parent
        self.settings = QSettings()
        self.asdGif = QMovie(PATH["ASD"])

        self.setup()

    def setup(self):
        self.init_buttons()
        self.init_line_edits()

        # Start the asd
        self.init_asd()

    def set_server_mode(self):
        """
        This function enables remote or local server mode, based on which radio button is pressed in NetworkSettings.
        """

        if self.localServerRadioButton.isChecked():  # Local mode
            self.parent.serverMode = LOCAL_MODE

            self.settings.setValue(LATEST_SERVER_IP, self.parent.host)
            self.settings.setValue(LATEST_SERVER_PORT, self.parent.port)

            self.parent.host = DEFAULT_IP
            self.parent.port = DEFAULT_PORT

            self.serverIpLineEdit.setText(self.parent.host)
            self.serverPortLineEdit.setText(str(self.parent.port))

            self.serverIpLineEdit.setReadOnly(True)

            self.defaultSystemLabel.setText("")

        elif self.remoteServerRadioButton.isChecked():  # Remote mode
            if not self.parent.serverMode:
                try:
                    self.parent.host = self.settings.value(LATEST_SERVER_IP)
                    self.parent.port = int(self.settings.value(LATEST_SERVER_PORT))
                except Exception as e:
                    print(f"ERROR: in NetworkSettings: {e}")
            self.parent.serverMode = REMOTE_MODE

            self.serverIpLineEdit.setText(self.parent.host)
            self.serverIpLineEdit.setReadOnly(False)

            self.serverPortLineEdit.setText(str(self.parent.port))
            self.serverPortLineEdit.setReadOnly(False)

            self.saveButton.setEnabled(True)

            self.defaultSystemLineEdit.setReadOnly(False)
            self.defaultSystemLabel.setText("When in remote mode, the user must insert manually the cannolo image directory.")

    def init_buttons(self):
        # init buttons
        self.saveButton.clicked.connect(self.save)
        self.cancelButton.clicked.connect(self.cancel)
        self.deleteConfigButton.clicked.connect(self.delete_config)
        self.findButton.clicked.connect(self.find_image)

        # init radio buttons
        if self.parent.serverMode == LOCAL_MODE:
            self.localServerRadioButton.setChecked(True)
        elif self.parent.serverMode == REMOTE_MODE:
            self.remoteServerRadioButton.setChecked(True)
        else:
            self.localServerRadioButton.setChecked(True)
        self.localServerRadioButton.clicked.connect(self.set_server_mode)
        self.remoteServerRadioButton.clicked.connect(self.set_server_mode)

        self.set_server_mode()

    def init_line_edits(self):
        # server ip
        self.serverIpLineEdit.setText(self.parent.host)
        self.load_completer()

        # server port
        if self.parent.port is not None:
            self.serverPortLineEdit.setText(str(self.parent.port))

        # default system path
        self.defaultSystemLineEdit.setText(self.parent.default_system_path)
        if self.parent.serverMode == REMOTE_MODE:
            self.defaultSystemLineEdit.setReadOnly(False)

    def init_asd(self):
        """Init the asd"""
        self.asdGif.setScaledSize(QSize().scaled(self.asdLabel.width(), self.asdLabel.height(), Qt.KeepAspectRatio))
        self.asdGif.start()
        self.asdLabel.setMovie(self.asdGif)

    def autocomplete_port(self, completion):
        # index = model.stringList().index(completion) if completion in model.stringList else -1
        self.settings.beginGroup(QSETTINGS_IP_GROUP)
        for key in self.settings.childKeys():
            if completion in self.settings.value(key):
                self.serverPortLineEdit.setText(self.settings.value(key)[1])
        self.settings.endGroup()

    def save(self):
        self.save_config()
        self.parent.host = self.serverIpLineEdit.text()
        self.parent.port = int(self.serverPortLineEdit.text())
        self.parent.default_system_path = self.defaultSystemLineEdit.text()

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

    def find_image(self):
        """
            This function opens a different dialog if
            the user is in local or remote mode to search for a cannolo image.
        """

        if self.parent.serverMode == REMOTE_MODE:
            directory = self.defaultSystemLineEdit.text()
            if directory ==  '':
                warning_dialog(
                    "Il path per l'immagine di sistema di default è vuoto. Impostalo plz.",
                    dialog_type="ok"
                )
                return
            splitted_dir = directory.rsplit("/", 1)
            if len(splitted_dir[1].split(".")) > 1:
                self.parent.client.send("list_iso " + directory.rsplit("/", 1)[0])
            else:
                if directory[-1] != "/":
                    directory += "/"
                self.parent.client.send("list_iso " + directory)

            if self.parent.select_system_dialog:
                self.parent.select_system_dialog.close()
            self.parent.select_system_dialog = SelectSystemDialog(self, False, directory)
        else:
            dialog = QFileDialog()
            # directory = dialog.getExistingDirectory(self, "Open Directory", "/home", QFileDialog.ShowDirsOnly)
            # directory = dialog.getExistingDirectory(self, "Open Directory", "/home")
            path = dialog.getOpenFileName(self, "Select new default image", "/home")[0]
            self.defaultSystemLineEdit.setText(path)
