import json
from PyQt5.QtGui import QFont, QBrush, QColor
from ui.SmartDataDialog import Ui_SmartDataDialog
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTreeWidgetItem, QFileDialog, QDialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pinolo import PinoloMainWindow

class SmartDialog(QDialog, Ui_SmartDataDialog):
    close_signal = pyqtSignal(QDialog)

    def __init__(self, parent: 'PinoloMainWindow', drive: str, smart_results: dict):
        super(SmartDialog, self).__init__(parent)
        self.setupUi(self)

        self.parent = parent
        self.drive = drive
        self.smart_results = json.loads(smart_results["output"])
        self.smart_status = smart_results["status"]

        self.setup()
        self.show()

    def setup(self):
        # setup window
        self.setWindowTitle(f"SMART data - {self.drive}")
        self.closeButton.clicked.connect(self.close)

        # status line setup
        self.statusLineEdit.setText(self.smart_status)
        match self.smart_status:
            case "ok":
                self.statusLineEdit.setStyleSheet("background-color: green; color: black;")
            case "old":
                self.statusLineEdit.setStyleSheet("background-color: yellow; color: black;")
            case _:
                self.statusLineEdit.setStyleSheet("background-color: red; color: black;")

        # tree widget setup
        self.populate_tree_widget(self.smart_results)
        self.treeWidget.itemExpanded.connect(self.resize_column)
        self.treeWidget.itemCollapsed.connect(self.resize_column)
        self.treeWidget.expandAll()
        self.treeWidget.addAction(self.actionExpand_All)
        self.treeWidget.addAction(self.actionCollapse_All)

        # search line edit setup
        self.searchLineEdit.textChanged.connect(self.highlight_items)

        # export data button
        self.exportButton.clicked.connect(self.export_data)

        # actions setup
        self.actionExpand_All.triggered.connect(self.treeWidget.expandAll)
        self.actionCollapse_All.triggered.connect(self.treeWidget.collapseAll)

    def populate_tree_widget(self, data, parent=None):
        if parent is None:
            parent = self.treeWidget

        for key, value in data.items():
            # Create a new tree widget item
            item = QTreeWidgetItem([str(key)])

            if parent == self.treeWidget:
                font = QFont()
                font.setBold(True)
                item.setFont(0, font)

            # If the value is a dictionary, recursively add children
            if isinstance(value, dict):
                self.populate_tree_widget(value, item)
            elif isinstance(value, list):
                # Handle lists of dictionaries
                for sub_item in value:
                    if isinstance(sub_item, dict):
                        # Create a parent item for this dictionary
                        dict_item = QTreeWidgetItem([str(key)])
                        item.addChild(dict_item)
                        self.populate_tree_widget(sub_item, dict_item)
                    else:
                        # Handle other types in the list
                        sub_item_widget = QTreeWidgetItem([str(sub_item)])
                        item.addChild(sub_item_widget)
            else:
                # If the value is not a dictionary, display it as a leaf node
                item.setText(1, str(value))

            # Add the item to the parent
            if parent == self.treeWidget:
                parent.addTopLevelItem(item)  # Add top-level item
            else:
                parent.addChild(item)  # Add as a child of the parent item

    def resize_column(self):
        self.treeWidget.resizeColumnToContents(0)

    def highlight_items(self, text):
        # Clear previous highlights
        self.clear_highlights()

        # If text is empty, return early
        if not text:
            return

        # Start searching from the root items
        for index in range(self.treeWidget.topLevelItemCount()):
            self.search_item(self.treeWidget.topLevelItem(index), text)

    def clear_highlights(self):
        for index in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(index)
            self.reset_item_background(item)

    def reset_item_background(self, item):
        item.setBackground(0, QBrush(QColor(255, 255, 255)))  # Reset background to white
        item.setBackground(1, QBrush(QColor(255, 255, 255)))  # Reset background to white

        # Check for children and reset their background
        for i in range(item.childCount()):
            self.reset_item_background(item.child(i))

    def search_item(self, item, text):
        # Check if the item text or value matches the search text
        key_match = text.lower() in item.text(0).lower()
        value_match = text.lower() in item.text(1).lower()

        # Highlight if there is a match
        if key_match or value_match:
            item.setBackground(0, QBrush(QColor(255, 255, 0)))  # Highlight key with yellow
            item.setBackground(1, QBrush(QColor(255, 255, 0)))  # Highlight value with yellow
            self.treeWidget.scrollToItem(item)

        # Recursively search in children
        for i in range(item.childCount()):
            self.search_item(item.child(i), text)

    def export_data(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Select File", "", "JSON Files (*.json);;All Files (*)", options=options)

        if file_path:
            with open(f"{file_path}.json", "w") as json_file:
                json.dump(self.smart_results, json_file, indent=4)

    def closeEvent(self, a0):
        self.close_signal.emit(self)