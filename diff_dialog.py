from PyQt5 import uic, QtWidgets, QtCore, QtGui
import sys


class DiffWidget(QtWidgets.QWidget):
    close_signal = QtCore.pyqtSignal(str, name="close")

    def __init__(self, reference: str, data: list):
        """ Set reference as the data that can identify the object that need features comparison.
         Example data list: [["type", "cpu", "ram"], ["working", "yes", "no"]] """

        super(DiffWidget, self).__init__()
        uic.loadUi("assets/qt/diff.ui", self)
        self.reference = reference
        self.data = data

        self.diffTableWidget = self.findChild(QtWidgets.QTableWidget, "diffTableWidget")
        self.diffTableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        for row, feature in enumerate(data):
            self.diffTableWidget.setRowCount(self.diffTableWidget.rowCount() + 1)
            button_group = QtWidgets.QButtonGroup(self)
            button_group.setExclusive(True)
            for col, cell in enumerate(feature):
                if col == 1 or col == 2:
                    checkbox = QtWidgets.QRadioButton(cell)
                    button_group.addButton(checkbox)
                    self.diffTableWidget.setCellWidget(row, col, checkbox)
                else:
                    self.diffTableWidget.setItem(row, col, QtWidgets.QTableWidgetItem(cell))

        self.show()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        header = self.diffTableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.diffTableWidget.resizeColumnToContents(1)
        self.diffTableWidget.setColumnWidth(1, self.diffTableWidget.columnWidth(1) + 20)
        self.diffTableWidget.resizeColumnToContents(2)
        self.diffTableWidget.setColumnWidth(2, self.diffTableWidget.columnWidth(2) + 20)
        self.diffTableWidget.setStyleSheet("QTableWidget::item { padding: 0 0 0 10px; }")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.close_signal.emit(self.reference)


def main():
    example = [
        ["type", "cpu", "ram"],
        ["working", "yes", "no"],
        ["capacity", "2.3Ghz", "2Gb"],
        ["socket", "775", "AM2"],
        ["Brand", "asdone", "lollone"],
    ]
    app = QtWidgets.QApplication(sys.argv)
    window = DiffWidget("asd", example)
    app.exec_()

if __name__ == "__main__":
    main()