#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 10:54:18 2021

@author: il_palmi
"""

import subprocess
import os
import paramiko

SPACE = 5
REQUIREMENTS = ["Model Family",
                "Device Model",
                "Serial Number",
                "Power_On_Hours",
                "Power_Cycle_Count",
                "SSD_Life_Left",
                "Lifetime_Writes_GiB",
                "Reallocated_Sector_Ct",
                "LU WWN Device Id",
                "Rotation Rate",
                "Current Pending Sector Count"]

SMARTCHECK = ["Power_On_Hours",
              "Reallocated_Sector_Cd",
              "Current Pending Sector Count"]

BLUE = "\033[36;40m"
RED = "\033[31;40m"
END_ESCAPE = "\033[0;0m"

IP = '192.168.2.3'
USER = 'piall'
PASSWD = 'asd'

def main():
    try:
        ssh = SshSession(IP,USER,PASSWD)
        ssh.initialize()
        drive = input("Inserire etichetta disco da analizzare (/dev/sd*): ")
        data, MAX = smartParser(drive, ssh)
        dataOutput(data, MAX)
        print("\n########################################################\n")
        smartAnalizer(data)
    except KeyboardInterrupt:
        print("Ok ciao")
    # input("Premere INVIO per uscire ...")


class SshSession:
    def __init__(self, ip, user, passwd):
        self.ip = ip
        self.user = user
        self.passwd = passwd
        self.session = paramiko.SSHClient()

    def initialize(self):
        self.session.load_system_host_keys()
        self.session.connect(self.ip, username=self.user, password=self.passwd)

    def kill(self):
        self.session.close()

    def execute(self, command):
        stdin, stdout, stderr = self.session.exec_command(command)
        output = []
        for line in stdout:
            output.append(line.rstrip('\n'))
        return output


def smartParser(drive: str, ssh):
    output = ssh.execute('sudo smartctl -a ' + drive)
    attributes = []
    for line in output:
        attributes.append(line)

    results = []
    fase = ""
    MAX = 0

    for attr in attributes:
        if attr == "=== START OF INFORMATION SECTION ===":
            fase = "INFO"
        elif attr == "=== START OF READ SMART DATA SECTION ===":
            fase = "SMART"
        if any(req for req in REQUIREMENTS if req in attr):
            if fase == "INFO":
                asd = attr.split(":")
                results.append([asd[0] , asd[1].lstrip()])
                if len(attr.split(":")[0]) > MAX:
                    MAX = len(attr.split(":")[0])
            elif fase == "SMART":
                splitted = attr.split()
                results.append([splitted[1] , splitted[8], splitted[9]])
                if len(splitted[1]) > MAX:
                    MAX = len(splitted[1])
    
    return results, MAX


def dataOutput(data, MAX):
    for row in data:
        temp = row[0]
        temp += ":"
        while len(temp) < MAX + SPACE:
            temp += " "
        if len(row) < 3:
            print(temp + row[1])
        else:
            print(temp + row[2])


def normalizer(rawValue):
    return(rawValue)

def smartAnalizer(data):
    for attribute in data:
        if attribute[0] == "Power_On_Hours":
            value = normalizer(attribute[2])
            if int(value) > 10000:
                check = "OLD"
            else:
                check = "OK"
        
        if len(attribute) == 3:
            if attribute[1].lstrip() != "-":
                check = "FAIL"
        
        if attribute[0] == "Current Pending Sector Count":
            value = normalizer(attribute[2])
            if int(value) > 0:
                check = "FAIL"
        
        if attribute[0] == "Reallocated_Sector_Ct":
            value = normalizer(attribute[2])
            if int(value) > 0:
                check = "FAIL"
                
        
    if check == "OK":
        print(BLUE + "SMART DATA CHECK  --->  OK" + END_ESCAPE)
    elif check == "OLD":
        print(BLUE + "SMART DATA CHECK  --->  OLD" + END_ESCAPE)
    elif check == "FAIL":
        print(RED + "SMART DATA CHECK  --->  FAIL\nHowever, check if the disc is functional" + END_ESCAPE)
    
    print("\nIl risultato è indicativo, non gettare l'hard disk se il check è FAIL")
            
# ---------------------------------------------------------------------


if __name__ == "__main__":
    main()
