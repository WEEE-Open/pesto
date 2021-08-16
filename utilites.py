import subprocess
import os
import paramiko
import socket
import sys
from PyQt5 import QtWidgets
import socket
import ast

def critical_dialog(message, type):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "Error!", message)
    if type == "ok":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    elif type == "yes_no":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
    return dialog.exec_()


def info_dialog(message):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Info", message)
    dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dialog.exec_()


def warning_dialog(message: str, type: str):
    if type == "yes_no":
        dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Warning", message)
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        return dialog.exec_()
    elif type == "ok":
        dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Warning", message)
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
        return dialog.exec_()


def win_path(path):
    new_path = r""
    for char in path:
        if char == '/':
            new_path += '\\'
        else:
            new_path += char
    new_path = os.path.dirname(os.path.realpath(__file__)) + new_path
    return new_path


def linux_path(path):
    new_path = os.path.dirname(os.path.realpath(__file__)) + path
    return new_path


def check_requirements(requirements_path):
    subprocess.Popen(["pip", "install", "-r", requirements_path])


def data_output(data, maximum):
    output = []
    space = 5
    for row in data:
        temp = row[0]
        temp += ":"
        while len(temp) < maximum + space:
            temp += " "
        if len(row) < 3:
            output.append(temp + row[1])
        else:
            output.append(temp + row[2])
    return output


def get_local_smart(platform: str, drive: str):
    attr = []
    if platform == 'win32':
        data = subprocess.getoutput("smartctl -a " + drive)
    else:
        data = subprocess.getoutput("sudo smartctl -a /dev/" + drive)
    data = data.split("\n")
    for line in data:
        attr.append(line)
    return attr


def smart_parser(drive: str, remoteMode: bool, platform: str, requirements: list):
    results = []
    fase = ""
    maximum = 0

    if remoteMode is False:
        data = get_local_smart(platform, drive)
    else:
        data = get_remote_smart(drive)

    for attr in data:
        if attr == "=== START OF INFORMATION SECTION ===":
            fase = "INFO"
        elif attr == "=== START OF READ SMART DATA SECTION ===":
            fase = "SMART"
        if any(req for req in requirements if req in attr):
            if fase == "INFO":
                asd = attr.split(":")
                results.append([asd[0], asd[1].lstrip()])
                if len(attr.split(":")[0]) > maximum:
                    maximum = len(attr.split(":")[0])
            elif fase == "SMART":
                splitted = attr.split()
                results.append([splitted[1], splitted[8], splitted[9]])
                if len(splitted[1]) > maximum:
                    maximum = len(splitted[1])
    return results, maximum


def smart_analyzer(data, text):
    check = ''
    for attribute in data:
        if attribute[0] == "Power_On_Hours":
            value = attribute[2]
            if int(value) > 10000:
                check = "OLD"
            else:
                check = "OK"

        if len(attribute) == 3:
            if attribute[1].lstrip() != "-":
                check = "FAIL"

        if attribute[0] == "Current Pending Sector Count":
            value = attribute[2]
            if int(value) > 0:
                check = "FAIL"

        if attribute[0] == "Reallocated_Sector_Ct":
            value = attribute[2]
            if int(value) > 0:
                check = "FAIL"

    if check == 'OK':
        text.append("SMART DATA CHECK  --->  OK")
    elif check == "OLD":
        text.append("SMART DATA CHECK  --->  OLD")
    elif check == "FAIL":
        text.append("SMART DATA CHECK  --->  FAIL\nHowever, check if the disc is functional")

    text.append("\nIl risultato è indicativo, non gettare l'hard disk se il check è FAIL")
    return text


def get_remote_smart(drive: str):
    attr = []
    cmd = "smartctl -a " + drive
    data = UDP_client(cmd).splitlines()
    for line in data:
        attr.append(line)
    return attr