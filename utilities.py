import subprocess
import os
import datetime
from typing import Optional
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QProgressBar, QWidget, QVBoxLayout
from constants import *


def critical_dialog(message, dialog_type):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "Error!", message)
    if dialog_type == "ok":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
        return dialog.exec_()
    elif dialog_type == "yes_no":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        return dialog.exec_()
    elif dialog_type == "ok_dna":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
        do_not_ask_btn = dialog.addButton("Don't ask again", dialog.ActionRole)
        dialog.setDefaultButton(QtWidgets.QMessageBox.Ok)
        dialog.exec_()
        if dialog.clickedButton() == do_not_ask_btn:
            return True
        else:
            return False


def info_dialog(message):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Info", message)
    dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dialog.exec_()


def warning_dialog(message: str, dialog_type: str):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Warning", message)
    if dialog_type == "yes_no":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        return dialog.exec_()
    elif dialog_type == "ok":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
        return dialog.exec_()
    elif dialog_type == "yes_no_chk":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        check_box = QtWidgets.QCheckBox("Click here to load cannolo image.")
        dialog.setCheckBox(check_box)
        result = [dialog.exec_(), True if check_box.isChecked() else False]
        return result
    elif dialog_type == "yes_no_cancel":
        dialog.addButton(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.addButton(QtWidgets.QMessageBox.Cancel)
        dialog.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        return dialog.exec_()


def input_dialog(message: str):
    dialog = QtWidgets.QInputDialog()
    loc, ok = dialog.getText(dialog, "Input dialog", message, QtWidgets.QLineEdit.Normal)
    return loc, ok


def check_requirements(requirements_path):
    p = subprocess.Popen(["pip", "install", "-r", requirements_path, "--quiet"])
    p.wait()


def absolute_path(big_path: {}):
    for path in big_path:
        big_path[path] = os.path.dirname(os.path.realpath(__file__)) + big_path[path]


def set_stylesheet(app, path):
    with open(path, "r") as file:
        app.setStyleSheet(file.read())


def format_size(size: int, round_the_result: bool = False, power_of_2: bool = True) -> str:
    if power_of_2:
        notation = ["B", "kiB", "MiB", "GiB", "TiB"]
        thousand = 1024
    else:
        notation = ["B", "kB", "MB", "GB", "TB"]
        thousand = 1000

    index = 0
    for count in range(0, len(notation)):
        if size >> (10 * count) == 0:
            index = count - 1
            break
    size = size / (thousand**index)
    if round_the_result:
        result = str(int(round(size)))
    else:
        result = "{:.2f}".format(size)
    result += f" {notation[index]}"
    return result


class SmartTabs(QtWidgets.QTabWidget):

    def __init__(self):
        super().__init__()
        self.color = None
        self.tabs = []
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(lambda index: self.removeTab(index))

    def add_tab(self, drive: str, status: Optional[str], uploaded: bool, text: list):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        text_box = QtWidgets.QTextEdit()
        text_box.setReadOnly(True)
        font = QtGui.QFont("Courier")
        font.setStyleHint(QtGui.QFont.TypeWriter)
        text_box.setFont(font)
        text_box.setFontPointSize(10)
        text_box.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        text_box.append("\n".join(text))
        if not status:
            status = "Errore deflagrante: impossibile determinare lo stato del disco."
        nowtime = datetime.datetime.now()
        label = QtWidgets.QLabel(f"Date: {nowtime.strftime('%H:%M:%S')}\nStatus: {status}\nUploaded: {uploaded}")
        label.setStyleSheet(f"color: {self.color}")
        layout.addWidget(label)
        layout.addWidget(text_box)
        widget.setLayout(layout)
        self.addTab(widget, drive)
        self.tabs.append(widget)


class ProgressBar(QWidget):

    def __init__(self):
        super(ProgressBar, self).__init__()

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100 * PROGRESS_BAR_SCALE)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.progress_bar)

    def setValue(self, value: int):
        self.progress_bar.setValue(value)
