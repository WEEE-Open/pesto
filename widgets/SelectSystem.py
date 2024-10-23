from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog

from ui.SelectSystemDialog import Ui_SelectSystemDialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pinolo import PinoloMainWindow
    from widgets.NetworkSettings import NetworkSettings


class SelectSystemDialog(QDialog, Ui_SelectSystemDialog):
    def __init__(self, parent: QObject, is_load_system: bool, path: str, images: list = None, network_settings_dialog: "NetworkSettings" = None):
        super(SelectSystemDialog, self).__init__(parent)
        self.setupUi(self)

        self.is_load_system = is_load_system
        self.path = path
        self.images = images
        self.network_settings_dialog = network_settings_dialog

        self.files = []

        self.setup()
        self.show()

    def setup(self):
        self.selectButton.clicked.connect(self.select)
        self.cancelButton.clicked.connect(self.close)

    def ask_for_image(self, images: list):
        self.images = images
        for img in images:
            img = img.rsplit("/", 1)[1]
            img = img.rsplit(".")
            if len(img) > 1:
                if img[1] == "iso" or img[1] == "img":
                    self.files.append(f"{img[0]}.{img[1]}")
        self.isoList.addItems(self.files)
        self.show()

    def select(self):
        """
        Selected iso from isoList is set as default system path in network settings.
        """

        if self.isoList.currentItem() is None:
            print("GUI: No image selected.")
            return

        iso = self.isoList.currentItem().text()
        for iso_dir in self.images:
            if iso in iso_dir:
                if self.is_load_system:
                    pinolo: "PinoloMainWindow" = self.parent()
                    pinolo.load_selected_system(iso_dir, iso)
                    break
                else:
                    network_settings: "NetworkSettings" = self.parent()
                    network_settings.defaultSystemLineEdit.setText(iso_dir)
                    break

        self.close()
