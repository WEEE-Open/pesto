import re
import subprocess
import os
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


def smartctl_get_status(smart: dict) -> str:
    """
    Get disk status from smartctl output.
    This algorithm has been mined: it's based on a decision tree with "accuracy" criterion since seems to produce
    slightly better results than the others. And the tree is somewhat shallow, which makes the algorithm more
    human-readable. There's no much theory other than that, so there's no real theory here.

    The data is about 200 smartctl outputs for every kind of hard disk, manually labeled with pestello (and mortaio)
    according to how I would classify them or how they are acting: if an HDD is making horrible noises and cannot
    perform a single read without throwing I/O errors, it's failed, no matter what the smart data says.

    Initially I tried to mix SSDs in, but their attributes are way different and they are also way easier to
    classify, so this algorithm works on mechanical HDDs only.

    This is the raw tree as output by RapidMiner:
    Current_Pending_Sector > 0.500
    |   Load_Cycle_Count = ?: FAIL {FAIL=9, SUS=0, OK=1, OLD=0}
    |   Load_Cycle_Count > 522030: SUS {FAIL=0, SUS=3, OK=0, OLD=0}
    |   Load_Cycle_Count ≤ 522030: FAIL {FAIL=24, SUS=0, OK=1, OLD=0}
    Current_Pending_Sector ≤ 0.500
    |   Reallocated_Sector_Ct = ?: OK {FAIL=1, SUS=0, OK=4, OLD=0}
    |   Reallocated_Sector_Ct > 0.500
    |   |   Reallocated_Sector_Ct > 3: FAIL {FAIL=8, SUS=1, OK=0, OLD=0}
    |   |   Reallocated_Sector_Ct ≤ 3: SUS {FAIL=0, SUS=4, OK=0, OLD=0}
    |   Reallocated_Sector_Ct ≤ 0.500
    |   |   Power_On_Hours = ?
    |   |   |   Run_Out_Cancel = ?: OK {FAIL=0, SUS=1, OK=3, OLD=1}
    |   |   |   Run_Out_Cancel > 27: SUS {FAIL=0, SUS=2, OK=0, OLD=0}
    |   |   |   Run_Out_Cancel ≤ 27: OK {FAIL=1, SUS=0, OK=6, OLD=1}
    |   |   Power_On_Hours > 37177.500
    |   |   |   Spin_Up_Time > 1024.500
    |   |   |   |   Power_Cycle_Count > 937.500: SUS {FAIL=0, SUS=1, OK=0, OLD=1}
    |   |   |   |   Power_Cycle_Count ≤ 937.500: OK {FAIL=0, SUS=0, OK=3, OLD=0}
    |   |   |   Spin_Up_Time ≤ 1024.500: OLD {FAIL=0, SUS=0, OK=2, OLD=12}
    |   |   Power_On_Hours ≤ 37177.500
    |   |   |   Start_Stop_Count = ?: OK {FAIL=0, SUS=0, OK=3, OLD=0}
    |   |   |   Start_Stop_Count > 13877: OLD {FAIL=1, SUS=0, OK=0, OLD=2}
    |   |   |   Start_Stop_Count ≤ 13877: OK {FAIL=2, SUS=9, OK=89, OLD=4}

    but some manual adjustments were made, just to be safe.
    Most HDDs are working so the data is somewhat biased, but there are some very obvious red flags like smartctl
    reporting failing attributes (except temperature, which doesn't matter and nobody cares) or having both
    reallocated AND pending sectors, where nobody would keep using that HDD, no matter what the tree decides.

    :param smart: Smartctl data
    :return: HDD status (label)
    """
    # Oddly the decision tree didn't pick up this one, but it's a pretty obvious sign the disk is failed
    if smart.get("Notsmart_Failing_Now", 0) > 0:
        return "fail"

    if int(smart.get("Current_Pending_Sector", 0)) > 0:
        # This part added manually just to be safe
        if int(smart.get("Reallocated_Sector_Ct", 0)) > 3:
            return "fail"

        # I wonder if this part is overfitted... who cares, anyway.
        cycles = smart.get("Load_Cycle_Count")
        if cycles:
            if int(cycles) > 522030:
                return "sus"
            else:
                return "fail"
        else:
            return "fail"
    else:
        reallocated = int(smart.get("Reallocated_Sector_Ct", 0))
        if reallocated > 0:
            if reallocated > 3:
                return "fail"
            else:
                return "sus"
        else:
            hours = smart.get("Power_On_Hours")
            if hours:
                # 4.2 years as a server (24/7), 15.2 years in an office pc (8 hours a day, 304 days a year)
                if int(hours) > 37177:
                    if int(smart.get("Spin_Up_Time", 0)) > 1024:
                        # Checking this attribute tells us if it's more likely to be a server HDD or an office HDD
                        if int(smart.get("Power_Cycle_Count", 0)) > 937:
                            # The tree says 1 old and 1 sus here, but there's too little data to throw around "sus"
                            # like this... it needs more investigation, though: if the disk is slow at starting up
                            # it may tell something about its components starting to fail.
                            return "old"
                        else:
                            return "ok"
                    else:
                        return "old"
                else:
                    # This whole area is not very good, but there are too many "ok" disks and too few not-ok ones
                    # to mine something better
                    if int(smart.get("Start_Stop_Count", 0)) > 13877:
                        return "old"
                    else:
                        return "ok"
            else:
                if int(smart.get("Run_Out_Cancel", 0)) > 27:
                    # Fun fact: I never looked at this attribute while classifying HDDs,
                    # but it is indeed a good indication that something is suspicious.
                    return "sus"
                else:
                    return "ok"
