import json
import sys
from variables import *
from typing import Any, Iterable, List, Dict, Union
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QAbstractItemModel, QModelIndex, QObject, Qt, QFileInfo
from PyQt5.QtWidgets import QWidget, QPushButton, QTreeView, QLineEdit, QTreeWidget


class SmartWidget(QWidget):
    close_signal = pyqtSignal(str, name="close")

    def __init__(self, drive: str, smart_results: dict):
        super(SmartWidget, self).__init__()
        uic.loadUi(PATH["SMART_UI"], self)
        self.drive = drive
        self.smart_results = json.loads(smart_results["output"])
        self.smart_status = smart_results["status"]

        self.setWindowTitle(f"SMART data - {self.drive}")

        self.closeButton = self.findChild(QPushButton, "closeButton")
        self.exportButton = self.findChild(QPushButton, "exportButton")

        self.treeView = self.findChild(QTreeView, "treeView")
        self.model = JsonModel()

        self.statusLineEdit = self.findChild(QLineEdit, "statusLineEdit")

        self.closeButton.clicked.connect(self.close)

        self.setup()

        self.show()

    def setup(self):
        # status line setup
        self.statusLineEdit.setText(self.smart_status)
        match self.smart_status:
            case "ok":
                self.statusLineEdit.setStyleSheet("background-color: green; color: black;")
            case "old":
                self.statusLineEdit.setStyleSheet("background-color: yellow; color: black;")
            case _:
                self.statusLineEdit.setStyleSheet("background-color: red; color: black;")

        # tree view setup
        self.treeView.setModel(self.model)
        self.model.load(self.smart_results)
        self.treeView.expandAll()
        self.treeView.resizeColumnToContents(0)


# Courtesy of pyqt documentation <3
class TreeItem:
    """A Json item corresponding to a line in QTreeView"""

    def __init__(self, parent: "TreeItem" = None):
        self._parent = parent
        self._key = ""
        self._value = ""
        self._value_type = None
        self._children = []

    def appendChild(self, item: "TreeItem"):
        """Add item as a child"""
        self._children.append(item)

    def child(self, row: int) -> "TreeItem":
        """Return the child of the current item from the given row"""
        return self._children[row]

    def parent(self) -> "TreeItem":
        """Return the parent of the current item"""
        return self._parent

    def childCount(self) -> int:
        """Return the number of children of the current item"""
        return len(self._children)

    def row(self) -> int:
        """Return the row where the current item occupies in the parent"""
        return self._parent._children.index(self) if self._parent else 0

    @property
    def key(self) -> str:
        """Return the key name"""
        return self._key

    @key.setter
    def key(self, key: str):
        """Set key name of the current item"""
        self._key = key

    @property
    def value(self) -> str:
        """Return the value name of the current item"""
        return self._value

    @value.setter
    def value(self, value: str):
        """Set value name of the current item"""
        self._value = value

    @property
    def value_type(self):
        """Return the python type of the item's value."""
        return self._value_type

    @value_type.setter
    def value_type(self, value):
        """Set the python type of the item's value."""
        self._value_type = value

    @classmethod
    def load(cls, value: Union[List, Dict], parent: "TreeItem" = None, sort=True) -> "TreeItem":
        """Create a 'root' TreeItem from a nested list or a nested dictonary

        Examples:
            with open("file.json") as file:
                data = json.dump(file)
                root = TreeItem.load(data)

        This method is a recursive function that calls itself.

        Returns:
            TreeItem: TreeItem
        """
        rootItem = TreeItem(parent)
        rootItem.key = "root"

        if isinstance(value, dict):
            items = sorted(value.items()) if sort else value.items()

            for key, value in items:
                child = cls.load(value, rootItem)
                child.key = key
                child.value_type = type(value)
                rootItem.appendChild(child)

        elif isinstance(value, list):
            for index, value in enumerate(value):
                child = cls.load(value, rootItem)
                child.key = index
                child.value_type = type(value)
                rootItem.appendChild(child)

        else:
            rootItem.value = value
            rootItem.value_type = type(value)

        return rootItem


class JsonModel(QAbstractItemModel):
    """An editable model of Json data"""

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._rootItem = TreeItem()
        self._headers = ("key", "value")

    def clear(self):
        """Clear data from the model"""
        self.load({})

    def load(self, document: dict):
        """Load model from a nested dictionary returned by json.loads()

        Arguments:
            document (dict): JSON-compatible dictionary
        """

        assert isinstance(document, (dict, list, tuple)), "`document` must be of dict, list or tuple, " f"not {type(document)}"

        self.beginResetModel()

        document = self.clean_document_from_bloat(document)

        self._rootItem = TreeItem.load(document)
        self._rootItem.value_type = type(document)

        self.endResetModel()

        return True

    def clean_document_from_bloat(self, document: dict):
        for key in IGNORE_SMART_RESULTS:
            document.pop(key, None)

        if "ata_smart_attributes" in document:
            attributes = {}
            for key in document["ata_smart_attributes"]["table"]:
                attributes[key["name"]] = key["value"]
            document.pop("ata_smart_attributes", None)
            document["attributes"] = attributes
        return document

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Any:
        """Override from QAbstractItemModel

        Return data from a json item according index and role

        """
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return item.key

            if index.column() == 1:
                return item.value

        elif role == Qt.EditRole:
            if index.column() == 1:
                return item.value

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole):
        """Override from QAbstractItemModel

        Set json item according index and role

        Args:
            index (QModelIndex)
            value (Any)
            role (Qt.ItemDataRole)

        """
        if role == Qt.EditRole:
            if index.column() == 1:
                item = index.internalPointer()
                item.value = str(value)

                if Qt.__binding__ in ("PySide", "PyQt4"):
                    self.dataChanged.emit(index, index)
                else:
                    self.dataChanged.emit(index, index, [Qt.EditRole])

                return True

        return False

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        """Override from QAbstractItemModel

        For the JsonModel, it returns only data for columns (orientation = Horizontal)

        """
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self._headers[section]

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        """Override from QAbstractItemModel

        Return index according row, column and parent

        """
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self._rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Override from QAbstractItemModel

        Return parent index of index

        """

        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self._rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        """Override from QAbstractItemModel

        Return row count from parent index
        """
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self._rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def columnCount(self, parent=QModelIndex()):
        """Override from QAbstractItemModel

        Return column number. For the model, it always return 2 columns
        """
        return 2

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Override from QAbstractItemModel

        Return flags of index
        """
        flags = super(JsonModel, self).flags(index)

        if index.column() == 1:
            return Qt.ItemIsEditable | flags
        else:
            return flags
