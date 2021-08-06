import subprocess
import os
import paramiko
import socket
import sys
from PyQt5 import QtWidgets


class SshSession:
    def __init__(self, ip, user, passwd):
        self.ip = ip
        self.user = user
        self.passwd = passwd
        self.session = paramiko.SSHClient()

    def initialize(self):
        self.session.load_system_host_keys()
        try:
            self.session.connect(self.ip, username=self.user, password=self.passwd)
            return True
        except paramiko.ssh_exception.AuthenticationException:
            message = "Authentication failed.\nCheck user and password."
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, ".Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False
        except socket.gaierror:
            message = "Cannot find ip address.\nCheck if you have inserted a wrong ip."
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False
        except paramiko.ssh_exception.NoValidConnectionsError:
            message = "Cannot find ip address.\nCheck if you have inserted a wrong ip."
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False
        except:
            message = str(sys.exc_info())
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Error!", message)
            dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            dialog.exec_()
            return False

    def kill(self):
        self.session.close()

    def execute(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        output = []
        for line in stdout:
            output.append(line.rstrip('\n'))
        return output


def critical_dialog(message, type):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "Error!", message)
    if type == "ok":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    elif type == "yes_no":
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
        dialog.addButton(QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
    dialog.exec_()


def info_dialog(message):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Info", message)
    dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dialog.exec_()


def warning_dialog(message):
    dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Warning", message)
    dialog.setStandardButtons(QtWidgets.QMessageBox.Yes)
    dialog.addButton(QtWidgets.QMessageBox.No)
    dialog.setDefaultButton(QtWidgets.QMessageBox.No)
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
