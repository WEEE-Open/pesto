import re
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


def parse_smartctl_output(smartctl) -> dict:
    found = {}
    errors = 0
    failing_now = 0

    info_section = False
    data_section = False
    errors_section = False
    for line in smartctl:
        line: str
        if "=== START OF INFORMATION SECTION ===" in line:
            info_section = True
            data_section = False
            errors_section = False
            continue
        if "=== START OF READ SMART DATA SECTION ===" in line:
            info_section = False
            data_section = True
            errors_section = False
            continue
        if "SMART Error Log Version" in line:
            info_section = False
            data_section = False
            errors_section = True
            continue
        if info_section:
            if 'Model Family: ' in line:
                val = line.split(':', 2)[1].strip()
                found["Notsmart_Brand"] = val.split(' ', 1)[0]
                found["Notsmart_Model_Family"] = val.strip()
                # Title case for UPPERCASE BRANDS (except IBM)
                if found["Notsmart_Brand"].isupper() and len(found["Notsmart_Brand"]) > 3:
                    found["Notsmart_Brand"] = found["Notsmart_Brand"].title()
            elif 'Serial Number:' in line:
                val = line.split('Serial Number:', 2)[1]
                found["Notsmart_Serial_Number"] = val.strip()

                # The WorkarounD:
                if found["Notsmart_Serial_Number"].startswith('WD-'):
                    found["Notsmart_Serial_Number"] = found["Notsmart_Serial_Number"][3:]

                if len(found["Notsmart_Serial_Number"]) <= 0:
                    del found["Notsmart_Serial_Number"]
            elif 'Rotation Rate:' in line:
                val = line.split(':', 2)[1].strip()
                if val.endswith("rpm"):
                    val = val[:-3].strip()
                found["Notsmart_Rotation_Rate"] = val
            continue
        if data_section:
            parts_test = line.strip().split(' ')
            try:
                param_value = int(parts_test[0].strip())
            except ValueError:
                continue
            if len(parts_test) >= 3 and 0 <= param_value <= 256:
                attr = parts_test[1].strip()

                if len(attr) <= 0:
                    continue
                if attr == "structures":
                    continue
                # Skip bad parsing (matching *******, "Not tested:", 0 and other strings)
                if len(re.sub('[a-zA-Z_]+', '', attr)) > 0:
                    continue

                if "FAILING_NOW" in line:
                    failing_now += 1

                val = line.rsplit("(")[0].split(" ")[-1].strip()
                if len(val) <= 0:
                    continue

                if 'h' in val and 'm' in val:
                    val = val.split("h")[0]
                    # noinspection PyBroadException
                    try:
                        minutes = int(val.split("h")[1].split("m")[0])
                        if minutes > 30:
                            val = str(int(val) + 1)
                    except BaseException:
                        pass
                elif 'Temperature' in attr:
                    continue
                elif '/' in val:
                    val.split('/')
                    if len(val[0].rstrip()) > 0:
                        val = val[0]
                    elif len(val[1].rstrip()) > 0:
                        val = val[1]
                    else:
                        continue
                found[attr] = val.rstrip()
            continue
        if errors_section:
            if 'Error: UNC' in line:
                errors += 1
        if errors > 0:
            found["Notsmart_Errors_UNC"] = errors
        found["Notsmart_Failing_Now"] = failing_now
    return found


def smartctl_get_status(found: dict) -> str:
    return "old"
