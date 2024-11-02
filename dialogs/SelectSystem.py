import os.path

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog

from ui.SelectSystemDialog import Ui_SelectSystemDialog


class SelectSystemDialog(QDialog, Ui_SelectSystemDialog):
    def __init__(self, parent: QObject):
        super(SelectSystemDialog, self).__init__(parent)
        self.setupUi(self)

        self.image_paths = []
        self.selected_image = None

        self.setup()
        self.show()

    def setup(self):
        self.selectButton.clicked.connect(self.select)
        self.cancelButton.clicked.connect(self.close)

    def load_images(self, images: list):
        for path in images:
            if not os.path.isfile(path):
                continue

            file_extension = os.path.splitext(path)[1]
            if file_extension == ".iso" or file_extension == ".img":
                self.isoList.addItem(os.path.basename(path))

    def select(self):
        """
        Selected iso from isoList is set as default system path in network settings.
        """

        if self.isoList.currentItem() is None:
            return

        self.selected_image = self.isoList.currentItem().text()
        self.accept()

    def get_selected_image(self):
        return self.selected_image
