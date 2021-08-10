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


def get_remote_smart(drive: str):
    attr = []
    cmd = "smartctl -a " + drive
    data = UDP_client(cmd).splitlines()
    for line in data:
        attr.append(line)
    return attr


def UDP_client(command: str, ip: str, port: int):
    MSG_FROM_CLIENT = command
    BYTES_TO_SEND = str.encode(MSG_FROM_CLIENT)
    SERVER_ADDRESS_PORT = (ip, port)
    BUFFER_SIZE = 1024

    # Create a client UDP socket
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

    # Send to server using client UDP socket
    UDPClientSocket.sendto(BYTES_TO_SEND, SERVER_ADDRESS_PORT)

    msgFromServer = UDPClientSocket.recvfrom(BUFFER_SIZE*3)
    msg = msgFromServer[0].decode('utf-8')
    return msg