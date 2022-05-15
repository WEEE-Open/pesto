#!/usr/bin/env python3

"""
WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING

This file was copied from peracotta.
If you want to make any changes, do them in peracotta first and then update this file.

WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
"""

from enum import Enum
import json
import sys
import re
from math import log10, floor
from typing import List, Dict

"""
Read "smartctl" output:
"""


class PORT(Enum):
    SATA = "sata-ports-n"
    MSATA = "msata-ports-n"
    IDE = "ide-ports-n"
    MINIIDE = "mini-ide-ports-n"
    M2 = "m2-connectors-n"
    # TODO: add more, if they can even be detected


def parse_smartctl(file: str, interactive: bool = False) -> List[dict]:
    """
    Parse a list of smartctl outputs to a list of disks.
    """
    disks = []
    jdisks = json.loads(file)
    for jdisk in jdisks:
        disk = parse_single_disk(jdisk, interactive)
        disks.append(disk)
    return disks


def seagate_model_decode(disk, model: str, maxtor: bool = False):
    # TODO: SCSI formats (https://hardforum.com/threads/understanding-hard-drive-model-numbers.921544/)
    old_format = r"STM?([0-9])[0-9]{2,}([A-Z][A-Z]?)*.*"

    if re.match(old_format, model):
        result = re.search(f"^{old_format}", model)
        ff_num = result.group(1)
        interface_num = result.group(2)

        ff = {
            "3": "3.5",
            "6": "1",
            "7": "1.8",
            "9": "2.5",
        }.get(ff_num)
        _add_feature_if_possible(disk, "hdd-form-factor", ff)

        if interface_num == "AS":
            _add_interface_if_possible(disk, "sata-ports-n")
        elif interface_num == "A":
            _add_interface_if_possible(disk, "ide-ports-n")

    if not maxtor:
        rpm = re.search(r"(?:.+ )*([1-9][0-9]00)\.[0-9]", disk.get("family", ""))
        if rpm:
            _add_feature_if_possible(disk, "spin-rate-rpm", int(rpm.group(1)))


def samsung_model_decode(disk, model: str):
    # SV + capacity (3) + number of heads (platters*2) + interface?
    sv_format = r"SV[0-9]{2,4}([A-Z])"

    if re.match(sv_format, model):
        result = re.search(f"^{sv_format}", model)

        if result.group(1) in ("C",):
            _add_interface_if_possible(disk, "sata-ports-n")
        elif result.group(1) in ("D", "E", "N", "H"):
            _add_interface_if_possible(disk, "ide-ports-n")


def hitachi_model_decode(disk, model: str):
    # https://www.instantfundas.com/2009/02/how-to-interpret-hard-disk-model.html
    h_format = r"H[A-Z][A-Z]([0-9]{2})[0-9]{2}[0-9]{2}[A-Z]([A-Z0-9])([A-Z][A-Z0-9])[0-9]+"
    ic25_format = r"IC(25|35)([A-Z])[0-9]{3}([A-Z0-9]{2})[A-Z0-9]{2}([0-9]{2})-?.*"

    if re.match(h_format, model):
        result = re.search(f"^{h_format}", model)
        rpm_num = result.group(1)
        ff_num = result.group(2)
        interface_num = result.group(3)

        rpm = {
            "36": 3600,
            "42": 4200,
            "54": 5400,
            "72": 7200,
            "10": 10000,
            "15": 15000,
        }.get(rpm_num)
        _add_feature_if_possible(disk, "spin-rate-rpm", rpm)

        ff = {
            "L": ("3.5", None),
            "S": ("2.5", 15),
            "9": ("2.5", 9.5),
            "8": ("2.5", 8),
            "7": ("2.5", 7),
            "5": ("2.5", 5),
        }.get(ff_num)
        if ff:
            _add_feature_if_possible(disk, "hdd-form-factor", ff[0])
            _add_feature_if_possible(disk, "height-mm", ff[1])

        if interface_num in ("A3", "SA"):
            _add_interface_if_possible(disk, "sata-ports-n")
        elif interface_num == "AT":
            _add_interface_if_possible(disk, "ide-ports-n")
    elif re.match(ic25_format, model):
        result = re.search(f"^{ic25_format}", model)
        ff_num = result.group(1)
        h_num = result.group(2)
        interface_num = result.group(3)
        rpm_num = result.group(4)

        ff = {
            "25": "2.5",
            "35": "3.5",
        }.get(ff_num)
        _add_feature_if_possible(disk, "hdd-form-factor", ff)

        h = {
            "L": 25.4,
            "T": 12.5,
            "N": 9.5,
        }.get(h_num)
        _add_feature_if_possible(disk, "height-mm", h)

        rpm = {
            "04": 4200,
            "05": 5400,
        }.get(rpm_num)
        _add_feature_if_possible(disk, "spin-rate-rpm", rpm)

        if interface_num in ("AV", "AT"):
            if ff == "2.5":
                _add_interface_if_possible(disk, "mini-ide-ports-n")
            else:
                _add_interface_if_possible(disk, "ide-ports-n")
        elif interface_num == "UC":
            _add_interface_if_possible(disk, "scsi-sca2-ports-n")
        elif interface_num == "UW":
            _add_interface_if_possible(disk, "scsi-db68-ports-n")


def toshiba_model_decode(disk, model: str):
    mk_format = r"MK[0-9]{2}[0-9]{2}G([A-Z])([A-Z])[A-Z]?"

    if re.match(mk_format, model):
        result = re.search(f"^{mk_format}", model)
        interface_num = result.group(1)
        ff_num = result.group(2)

        ff = {
            "A": ("1.8", 5, 3600),
            "B": ("1.8", 8, 3600),
            "G": ("1.8", 8, 5400),
            "H": ("1.8", 8, 4200),
            "L": ("1.8", 5, 4200),
            "K": ("3.5", None, 7200),
            "M": ("2.5", 12.7, 5400),
            "P": ("2.5", None, 4200),
            "R": ("2.5", None, 15000),
            "S": ("2.5", 9.5, 4200),
            "X": ("2.5", 9.5, 5400),
            "Y": ("2.5", 9.5, 7200),
        }.get(ff_num)
        if ff:
            _add_feature_if_possible(disk, "hdd-form-factor", ff[0])
            _add_feature_if_possible(disk, "height-mm", ff[1])
            _add_feature_if_possible(disk, "spin-rate-rpm", ff[2])

        interface = {
            "A": "mini-ide-ports-n" if ff and ff[0] != "3.5" else "ide-ports-n",
            "P": "mini-ide-ports-n",
            "R": "sas-sata-ports-n",
            "S": "sata-ports-n",
        }.get(interface_num)
        _add_interface_if_possible(disk, interface)


def fujitsu_model_decode(disk, model: str):
    mhx2_format = r"MH[A-Z](2|3)[0-9]{3}([A-Z]{2})U?(?: .+)?"

    if re.match(mhx2_format, model):
        result = re.search(f"^{mhx2_format}", model)
        ff_num = result.group(1)
        extra_num = result.group(2)

        ff = {
            "2": "2.5",
            "3": "3.5",
        }.get(ff_num)
        _add_feature_if_possible(disk, "hdd-form-factor", ff)

        ide = "ide-ports-n"
        if ff == "2.5":
            ide = "mini-ide-ports-n"

        extra = {
            "AH": (ide, 5400),
            "AS": (ide, 5400),
            "AT": (ide, 4200),
            "BH": ("sata-ports-n", 5400),
            "BS": ("sata-ports-n", 5400),
            "BT": ("sata-ports-n", 4200),
        }.get(extra_num)
        if extra:
            _add_interface_if_possible(disk, extra[0])
            _add_feature_if_possible(disk, "spin-rate-rpm", extra[1])

        # _add_feature_if_possible(disk, "height-mm", 9.5)


def quantum_model_decode(disk, model: str):
    if model.lower().startswith("fireball"):
        _add_interface_if_possible(disk, "ide-ports-n")


def wd_model_decode(disk, model: str):
    old_format = r"WD[0-9]{2,4}([A-Z])([A-Z])-.+"
    new_format = r"WD[0-9]{4}([A-Z])[A-Z]([A-Z])([A-Z])-.+"

    if re.match(old_format, model):
        result = re.search(f"^{old_format}", model)
        rpm_num = result.group(1)
        interface_num = result.group(2)

        rpm = {
            "A": 5400,
            "B": 7200,
            "C": 10000,
            "D": 4500,
            "E": 5400,
            "F": 10000,
            "G": 10000,
            "H": 10000,
            "J": 7200,
            "K": 7200,
            "L": 7200,
            "M": 5400,
            "N": 5400,
            "P": 7200,
            "R": 10000,
            "S": 7200,
            "T": 7200,
            "U": 5400,
            "V": 5400,
            "W": 3600,
            "X": 4200,
            "Y": 7200,
            "Z": 7200,
        }.get(rpm_num)
        _add_feature_if_possible(disk, "spin-rate-rpm", rpm)

        interface = {
            "A": "ide-ports-n",
            "B": "ide-ports-n",
            "C": "firewire-ports-n",
            "D": "sata-ports-n",
            "E": "ide-ports-n",
            "R": "sata-ports-n",
            "S": "sata-ports-n",
        }.get(interface_num)
        _add_interface_if_possible(disk, interface)

    elif re.match(new_format, model):
        result = re.search(f"^{new_format}", model)
        ff_num = result.group(1)
        rpm_num = result.group(2)
        interface_num = result.group(3)

        ff = {
            "A": ("3.5", None),
            "B": ("2.5", None),
            "C": ("1.0", None),
            "E": ("3.5", None),
            "F": ("3.5", None),
            # "G": "",
            # "H": "",
            "J": ("2.5", 9.5),
            "K": ("3.5", None),
            "L": ("2.5", 7),
            "M": ("2.5", 5),
            "N": ("2.5", 15),
            "P": ("3.5", None),
            "S": ("2.5", 7),
            "T": ("2.5", 12.5),
            "X": ("2.5", 9.5),
        }.get(ff_num)
        if ff:
            _add_feature_if_possible(disk, "hdd-form-factor", ff[0])
            _add_feature_if_possible(disk, "height-mm", ff[1])

        rpm = {
            "A": 5400,
            "B": 7200,
            "C": 5400,
            "D": 5400,
            "E": 7200,
            "F": 10000,
            "G": 10000,
            "H": 10000,
            "J": 7200,
            "K": 7200,
            "L": 7200,
            "P": 5400,
            "R": 5400,
            "S": 7200,
            "T": 10000,
            "V": 5400,
            "W": 7200,
            "Y": 7200,
            "Z": 5400,
        }.get(rpm_num)
        _add_feature_if_possible(disk, "spin-rate-rpm", rpm)

        interface = {
            "A": "ide-ports-n",
            "B": "ide-ports-n",
            "D": "sata-ports-n",
            "E": "ide-ports-n",
            "F": "sas-sata-ports-n",
            "G": "sas-sata-ports-n",
            "K": "sata-ports-n",
            "S": "sata-ports-n",
            "T": "sata-ports-n",
            "W": "usb-ports-n",
            "X": "sata-ports-n",
            "Z": "sata-ports-n",
        }.get(interface_num)
        _add_interface_if_possible(disk, interface)


def maxtor_model_decode(disk, model: str):
    the_format = r"([0-9][A-Z])[0-9]{2,3}([A-Z])[0-9]"

    if re.match(the_format, model):
        result = re.search(f"^{the_format}", model)
        series_num = result.group(1)
        interface_num = result.group(2)

        ff = {
            "4D": "3.5",
            "4G": "3.5",
            "4K": "3.5",
            "6L": "3.5",
            "6E": "3.5",
            "6Y": "3.5",
        }.get(series_num)
        _add_feature_if_possible(disk, "hdd-form-factor", ff)

        interface = {
            "D": "ide-ports-n",
            "F": "sata-ports-n",
            "H": "ide-ports-n",
            "J": "ide-ports-n",
            "K": "ide-ports-n",
            "L": "ide-ports-n",
            "M": "sata-ports-n",
            "P": "ide-ports-n",
            "R": "ide-ports-n",
            "S": "sata-ports-n",
            "U": "ide-ports-n",
        }.get(interface_num)
        _add_interface_if_possible(disk, interface)
    else:
        seagate_model_decode(disk, model, True)


def _add_feature_if_possible(disk, feature, value):
    if value is not None:
        if feature not in disk:
            if value:
                disk[feature] = value


def _add_interface_if_possible(disk, interface):
    interface_values = [
        "ide-ports-n",
        "sata-ports-n",
        "firewire-ports-n",
        "sas-sata-ports-n",
        "usb-ports-n",
        "scsi-sca2-ports-n",
        "scsi-db68-ports-n",
    ]

    if interface:
        if interface not in disk:
            for maybe_interface in interface_values:
                if maybe_interface in disk:
                    # TODO: print a warning
                    break
            else:
                disk[interface] = 1


def parse_single_disk(smartctl: dict, interactive: bool = False) -> dict:
    """
    Parse a single disk from smartctl -ja output to tarallo upload format.

    See parse_smartctl to parse multiple disks.
    """
    disk = {
        "type": "hdd",
    }

    # json_format_version is [1,0], anything else and this parser will catch fire

    port = None

    if smartctl.get("vendor") and smartctl.get("product"):
        # For SCSI disks only, apparently
        disk["brand"] = smartctl.get("vendor")
        disk["model"] = smartctl.get("product")
    else:
        # "Device Model:" is model_name in the JSON
        if smartctl.get("model_name"):
            brand, model = _split_brand_and_other(smartctl.get("model_name"))
            disk["model"] = model
            if "brand" not in disk and brand:
                disk["brand"] = brand

        if smartctl.get("model_family"):
            brand, family = _split_brand_and_other(smartctl.get("model_family"))
            disk["family"] = family
            if "brand" not in disk and brand:
                disk["brand"] = brand

    if disk.get("brand", "") == "WDC":
        disk["brand"] = "Western Digital"

    if smartctl.get("serial_number"):
        disk["sn"] = smartctl.get("serial_number")

    if smartctl.get("wwn"):
        disk["wwn"] = str(smartctl["wwn"].get("naa", "")) + " " + str(smartctl["wwn"].get("oui", "")) + " " + str(smartctl["wwn"].get("id", ""))

    if smartctl.get("form_factor", {}).get("name"):
        ff = smartctl["form_factor"]["name"]
        # https://github.com/smartmontools/smartmontools/blob/master/smartmontools/ataprint.cpp#L405
        if ff == "3.5 inches":
            disk["hdd-form-factor"] = "3.5"
        elif ff == "2.5 inches":
            disk["hdd-form-factor"] = "2.5"
        elif ff == "1.8 inches":
            disk["hdd-form-factor"] = "1.8"
        # TODO: add these to tarallo
        elif ff == "M.2":
            disk["hdd-form-factor"] = "m2"
            port = PORT.M2
        elif ff == "mSATA":
            disk["hdd-form-factor"] = "msata"
            port = PORT.MSATA

    if smartctl.get("user_capacity", {}).get("bytes"):
        # https://stackoverflow.com/a/3411435
        round_digits = int(floor(log10(abs(float(smartctl["user_capacity"]["bytes"]))))) - 2
        bytes_rounded = int(round(float(smartctl["user_capacity"]["bytes"]), -round_digits))
        disk["capacity-decibyte"] = bytes_rounded

    # This may be 0, which is a valid value and casts to False, check for None explicitly!
    if smartctl.get("rotation_rate") is not None:
        if smartctl.get("rotation_rate") > 0:
            disk["spin-rate-rpm"] = smartctl.get("rotation_rate")
            disk["type"] = "hdd"
        else:
            disk["type"] = "ssd"

    if disk.get("brand", "").title() == "Western Digital":
        # These are useless and usually not even printed on labels and in bar codes...
        if "model" in disk:
            disk["model"] = _remove_prefix("WDC ", disk["model"])
        if "sn" in disk:
            disk["sn"] = _remove_prefix("WD-", disk["sn"])

    if "SSD " in disk.get("model", "") or " SSD" in disk.get("model", ""):
        disk["model"] = disk["model"].replace("SSD ", "").replace(" SSD", "")
        _mega_clean_disk_model(disk)
        if disk["type"] == "hdd":
            disk["type"] = "ssd"

    if "(SATA)" in disk.get("family", ""):
        disk["family"] = disk.get("family").replace("(SATA)", "").strip()

    if "(ATA/133 and SATA/150)" in disk.get("family", ""):
        disk["family"] = disk.get("family").replace("(ATA/133 and SATA/150)", "").strip()

    if "SSD" in disk.get("family", ""):
        if disk["type"] == "hdd":
            disk["type"] = "ssd"
        lowered = disk["family"].replace(" ", "").lower()
        if lowered in ("basedssds", "basedssd"):
            del disk["family"]

    if disk.get("family", "").startswith("/"):
        disk["family"] = disk.get("family", "")[1:]

    if "Serial ATA" in disk.get("family", ""):
        if not port:
            port = PORT.SATA
        disk["family"] = disk.get("family").replace("Serial ATA", "").strip()

    if disk.get("model", "").startswith("HGST "):
        disk["model"] = disk.get("model")[5:]
        disk["brand-manufacturer"] = "HGST"

    # Unreliable port detection as a fallback
    if port is None:
        if "SATA" in disk.get("family", "") or "SATA" in disk.get("model", ""):
            port = PORT.SATA
        if "Serial ATA" in disk.get("family", ""):
            # disk["family"] = disk["family"].replace("Serial ATA", "").strip()
            port = PORT.SATA
        if "sata_version" in smartctl:
            port = PORT.SATA
        elif "pata_version" in smartctl:
            if disk.get("hdd-form-factor", "").startswith("2.5") or disk.get("hdd-form-factor", "").startswith("1.8"):
                port = PORT.MINIIDE
            else:
                port = PORT.IDE
        if "nvme_version" in smartctl:
            port = PORT.M2
            if disk.get("type", "") == "hdd":
                disk["type"] = "ssd"
            if "hdd-form-factor" not in disk:
                disk["hdd-form-factor"] = "m2"
        if "device" in smartctl and smartctl["device"].get("type", "") == "scsi" and smartctl["device"].get("protocol", "") == "SCSI":
            disk["notes"] = "This is a SCSI disk, however it is not possible to detect the exact connector type. Please set the correct one manually."

    if port is not None:
        disk[port.value] = 1

    # FF detector
    if "hdd-form-factor" not in disk:
        if "desktop" in disk.get("family", "").lower() and port == PORT.SATA:
            disk["hdd-form-factor"] = "3.5"

    if disk.get("model") is not None:
        brand = disk.get("brand")
        if brand == "Western Digital":
            wd_model_decode(disk, disk.get("model"))
        elif brand == "Seagate":
            seagate_model_decode(disk, disk.get("model"))
        elif brand == "Maxtor":
            maxtor_model_decode(disk, disk.get("model"))
        elif brand == "Samsung":
            samsung_model_decode(disk, disk.get("model"))
        elif brand == "Toshiba":
            toshiba_model_decode(disk, disk.get("model"))
        elif brand == "Fujitsu":
            fujitsu_model_decode(disk, disk.get("model"))
        elif brand == "Hitachi":
            hitachi_model_decode(disk, disk.get("model"))
        elif brand == "Quantum":
            quantum_model_decode(disk, disk.get("model"))

    smart, failing_now = extract_smart_data(smartctl)

    status = smart_health_status(smart, failing_now)
    if status:
        if len(smart) < 2 and status == "ok":
            # Nah bro, I'll pass... "ok" with (nearly) no smart data is meaningless
            pass
        else:
            disk["smart-data"] = status
    else:
        if interactive:
            print("Failed to determine HDD health status from SMART data!")
        pass

    return disk


def extract_smart_data(parsed: dict) -> [Dict, bool]:
    """
    Extract SMART attributes and raw values from smartctl -ja output.
    Also returns failing_now value to indicate if any attributes (except temperature)
    is failing now.
    """
    failing_now = False

    smart = {}
    if parsed.get("ata_smart_attributes", {}).get("table"):
        for line in parsed["ata_smart_attributes"]["table"]:
            # Name
            name = line["name"]

            # Value
            if name.lower() == "unknown_attribute":
                name = f"{name}_{str(line['id'])}"
            value = line["raw"]["value"]

            # Normalize power on time to hours
            # (see https://github.com/mirror/smartmontools/blob/44cdd4ce63ca4e07db87ec062a159181be967a72/ataprint.cpp#L1140-L1168)
            if line["id"] == 9 and name.lower().startswith("power_on_"):
                if "power_on_time" in parsed:
                    if parsed["power_on_time"].get("hours", None) is not None:
                        value = parsed["power_on_time"]["hours"]
                    elif parsed["power_on_time"].get("minutes", None) is not None:
                        value = parsed["power_on_time"]["minutes"] * 60
            # Set result
            smart[name] = value

            # Find out if anything is failing
            if "when_failed" in line:
                if line["when_failed"] == "now":
                    if line["name"].lower() != "temperature_celsius":
                        failing_now = True
    return smart, failing_now


def _mega_clean_disk_model(disk: dict):
    disk["model"] = disk["model"].replace("  ", " ").strip()
    if disk["model"] == "":
        del disk["model"]


def smart_health_status(smart: dict, failing_now: bool) -> str:
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

    :param failing_now: If any attribute is marked as failing
    :param smart: Smartctl data
    :return: HDD status (label)
    """
    # Oddly the decision tree didn't pick up this one, but it's a pretty obvious sign the disk is failed
    if failing_now:
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


def _split_brand_and_other(line):
    lowered = line.lower()

    possibilities = [
        "WDC ",
        "Western Digital",
        "Seagate",
        "Maxtor",
        "Hitachi",
        "Toshiba",
        "Samsung",
        "Fujitsu",
        "Apple",
        "Crucial/Micron",
        "Crucial",
        "LiteOn",
        "Kingston",
        "Adata",
        "Quantum",
    ]

    brand = None
    other = line
    for possible in possibilities:
        if lowered.startswith(possible.lower()):
            brand = possible.strip()
            other = line[len(possible) :].lstrip("_").strip()
            break

    return brand, other


def _remove_prefix(prefix, text):
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


if __name__ == "__main__":
    try:
        with open(sys.argv[1], "r") as f:
            input_file = f.read()
        print(json.dumps(parse_smartctl(input_file), indent=2))
    except BaseException as e:
        print(str(e))
        exit(1)
