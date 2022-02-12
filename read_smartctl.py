#!/usr/bin/env python3

from enum import Enum
import json
import sys
from math import log10, floor
from typing import List

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
    disks = []
    jdisks = json.loads(file)
    for jdisk in jdisks:
        disk = _parse_disk(jdisk)
        disks.append(disk)
    return disks


def _parse_disk(file):
    disk = {
        "type": "hdd",
    }

    # json_format_version is [1,0], anything else and this parser will catch fire

    port = None

    if file.get("vendor") and file.get("product"):
        # For SCSI disks only, apparently
        disk["brand"] = file.get("vendor")
        disk["model"] = file.get("product")
    else:
        if file.get("model_name"):
            brand, model = _split_brand_and_other(file.get("model_name"))
            disk["model"] = model
            if "brand" not in disk and brand:
                disk["brand"] = brand

        if file.get("model_family"):
            brand, family = _split_brand_and_other(file.get("model_family"))
            disk["family"] = family
            if "brand" not in disk and brand:
                disk["brand"] = brand

        if file.get("device_model"):  # TODO: does this exist?
            brand, model = _split_brand_and_other(file.get("device_model"))
            disk["model"] = model
            if "brand" not in disk and brand:
                disk["brand"] = brand

    if disk.get("brand", "") == "WDC":
        disk["brand"] = "Western Digital"

    if file.get("serial_number"):
        disk["sn"] = file.get("serial_number")

    if file.get("wwn"):
        disk["wwn"] = (
            str(file["wwn"].get("naa", ""))
            + " "
            + str(file["wwn"].get("oui", ""))
            + " "
            + str(file["wwn"].get("id", ""))
        )

    if file.get("form_factor", {}).get("name"):
        ff = file["form_factor"]["name"]
        # https://github.com/smartmontools/smartmontools/blob/master/smartmontools/ataprint.cpp#L405
        if ff == "3.5 inches":
            disk["hdd-form-factor"] = "3.5"
        elif ff == "2.5 inches":
            # This is the most common height, just guessing...
            disk["hdd-form-factor"] = "2.5-7mm"
        elif ff == "1.8 inches":
            # Still guessing...
            disk["hdd-form-factor"] = "1.8-8mm"
        # TODO: add these to tarallo
        elif ff == "M.2":
            disk["hdd-form-factor"] = "m2"
            port = PORT.M2
        elif ff == "mSATA":
            disk["hdd-form-factor"] = "msata"
            port = PORT.MSATA

    if file.get("user_capacity", {}).get("bytes"):
        # https://stackoverflow.com/a/3411435
        round_digits = int(floor(log10(abs(float(file["user_capacity"]["bytes"]))))) - 2
        bytes_rounded = int(round(float(file["user_capacity"]["bytes"]), -round_digits))
        disk["capacity-decibyte"] = bytes_rounded

    # This may be 0, which is a valid value and casts to False, check for None explicitly!
    if file.get("rotation_rate") is not None:
        if file.get("rotation_rate") > 0:
            disk["spin-rate-rpm"] = file.get("rotation_rate")
            disk["type"] = "hdd"
        else:
            disk["type"] = "ssd"

    # TODO: throw a catastrophic fatal error of death if a disk has SMART disabled (can be enabled and disabled with smartctl to test and view the exact error message)
    # TODO: NVME support

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

    if "SSD" in disk.get("family", ""):
        if disk["type"] == "hdd":
            disk["type"] = "ssd"
        lowered = disk["family"].replace(" ", "").lower()
        if lowered in ("basedssds", "basedssd"):
            del disk["family"]

    # Unreliable port detection as a fallback
    if port is None:
        if "SATA" in disk.get("family", "") or "SATA" in disk.get("model", ""):
            port = PORT.SATA
        if "Serial ATA" in disk.get("family", ""):
            # disk["family"] = disk["family"].replace("Serial ATA", "").strip()
            port = PORT.SATA
        if "sata_version" in file:
            port = PORT.SATA
        elif "pata_version" in file:
            if disk.get("hdd-form-factor", "").startswith("2.5") or disk.get(
                "hdd-form-factor", ""
            ).startswith("1.8"):
                port = PORT.MINIIDE
            else:
                port = PORT.IDE
        if "nvme_version" in file:
            port = PORT.M2
            if disk.get("type", "") == "hdd":
                disk["type"] = "ssd"
            if "hdd-form-factor" not in disk:
                disk["hdd-form-factor"] = "m2"
        if (
            "device" in file
            and file["device"].get("type", "") == "scsi"
            and file["device"].get("protocol", "") == "SCSI"
        ):
            disk[
                "notes"
            ] = "This is a SCSI disk, however it is not possible to detect the exact connector type. Please set the correct one manually."

    if port is not None:
        disk[port.value] = 1

    # FF detector
    if "hdd-form-factor" not in disk:
        if "desktop" in disk.get("family", "").lower() and port == PORT.SATA:
            disk["hdd-form-factor"] = "3.5"

    smart = extract_smart_data(file)

    # TODO: failing now, uncorrectable error log, other stuff
    status = smart_health_status(smart, False)
    if status:
        if len(smart) < 2 and status == "ok":
            # Nah bro, I'll pass... "ok" with (nearly) no smart data is meaningless
            pass
        else:
            disk["smart-data"] = status
    else:
        # TODO: print verbose error
        pass

    return disk


def extract_smart_data(parsed):
    smart = {}
    if parsed.get("ata_smart_attributes", {}).get("table"):
        for line in parsed["ata_smart_attributes"]["table"]:
            name = line["name"]
            if name.lower() == "unknown_attribute":
                name = f"{name}_{str(line['id'])}"
            smart[name] = line["raw"]["value"]
    return smart


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
