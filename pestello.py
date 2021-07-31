#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import argparse
import os
import traceback

RED = "\033[31;40m"
END_ESCAPE = "\033[0;0m"


def get_files(paths, quiet: bool):
    filenames = []
    results = []
    serials = set()
    errors = False
    counter = 1
    already_labeled = {}

    try:
        with open('labeled_out.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                if 'Serial_Number' in row and 'Status' in row:
                    already_labeled[row['Serial_Number']] = row
    except FileNotFoundError:
        print("No labeled_out.csv found")

    print(f"Found {len(already_labeled)} labels\n")

    for file in paths:
        file: str
        if os.path.isdir(file):
            for filename in os.listdir(file):
                filenames.append(file.rstrip('/') + '/' + filename)
        elif os.path.isfile(file):
            filenames.append(file)
        else:
            print(f"{file} is not a file nor a directory")
            errors = True

    for filename in filenames:
        try:
            parse_file(filename, results, serials, counter, already_labeled, quiet)
            counter += 1
        except (KeyboardInterrupt, EOFError):
            break
        except:
            print(f"Error reading {filename}")
            print(traceback.format_exc())
            pass

    print(f"{len(serials)} unique disks parsed, {len(results)} labeled")

    if len(already_labeled) > 0:
        print(f"Merging {len(already_labeled)} old labels")
        results += list(already_labeled.values())

    header = []
    header_set = set()
    for result in results:
        for k in result:
            if k != 'Status' and k not in header_set:
                header_set.add(k)
                header.append(k)
    header_set.add('Status')
    header.append('Status')
    print(header)

    with open('labeled.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, fieldnames=header)
        writer.writeheader()

        for result in results:
            writer.writerow(result)

    if errors:
        exit(1)


def parse_file(filename: str, results: list, serials: set, counter: int, already_labeled: dict, quiet: bool):
    print(f"File {counter} - {filename}")

    found = dict()
    errors = 0

    found_at_least_one = False
    with open(filename, 'r') as f:
        info_section = False
        data_section = False
        errors_section = False
        for line in f:
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
                    found["Brand"] = val.split(' ', 1)[0]
                    found["Model_Family"] = val.strip()
                    # Title case for UPPERCASE BRANDS (except IBM)
                    if found["Brand"].isupper() and len(found["Brand"]) > 3:
                        found["Brand"] = found["Brand"].title()
                if 'Serial Number:' in line:
                    val = line.split('Serial Number:', 2)[1]
                    found["Serial_Number"] = val.strip()
                    if len(found["Serial_Number"]) <= 0:
                        del found["Serial_Number"]
                continue
            if data_section:
                parts_test = line.split(' ')
                try:
                    param_value = int(parts_test[0])
                except ValueError:
                    continue
                if len(parts_test) >= 3 and 0 <= param_value <= 256:
                    found_at_least_one = True
                    attr = parts_test[1]
                    val = line.split("(")[0].split(" ")[-1].strip()
                    if 'h' in val and 'm' in val:
                        val = val.split("h")[0]
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

    found["Errors_UNC"] = str(errors)

    if "Serial_Number" not in found:
        found["Serial_Number"] = filename
    if found["Serial_Number"] in serials:
        print(f"Skipping duplicate {found['Serial_Number']}\n")
        return
    else:
        serials.add(found["Serial_Number"])

    if not found_at_least_one:
        print(f"Skipping empty disk")
        return

    if not quiet or not found['Serial_Number'] in already_labeled:
        for k in found:
            details = ""
            if k == "Total_LBAs_Written":
                details = f" ({int(found[k])*512/1024/1024/1024:.2f} GiB)"
            elif k == "Power_On_Hours":
                try:
                    server = int(found[k]) / 24 / 365
                    office = int(found[k]) / 8 / 304
                    details = f" ({server:.2f} server years, {office:.2f} office years)"
                    if server >= 20:
                        details += f" (or, if minutes, {server/60:.2f} server years, {office/60:.2f} office years)"
                except:
                    pass
            if k != "Serial_Number" and found[k].isnumeric() and int(found[k]) != 0:
                color1 = RED
                color2 = END_ESCAPE
            else:
                color1 = color2 = ""
            print(f"{k}: {color1}{found[k]}{color2}{details}")

    answered = False
    question = "Is it OK, SUS, OLD, FAIL or discard? [K,S,O,F,X] "

    if found['Serial_Number'] in already_labeled:
        old_labeled_row = already_labeled[found['Serial_Number']]
        print(f"{question}{old_labeled_row['Status']} (already labeled)")
        found['Status'] = old_labeled_row['Status']
        results.append(found)
        answered = True
        del already_labeled[found['Serial_Number']]

    while not answered:
        r = input(question)
        r = r.lower()
        if r == 'k' or r == 'y':
            found['Status'] = 'OK'
            results.append(found)
            answered = True
        elif r == 'o':
            found['Status'] = 'OLD'
            results.append(found)
            answered = True
        elif r == 'f':
            found['Status'] = 'FAIL'
            results.append(found)
            answered = True
        elif r == 's':
            found['Status'] = 'SUS'
            results.append(found)
            answered = True
        elif r == 'x':
            answered = True
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Classify SMART data manually. Now.')
    parser.add_argument('files', nargs='+', type=str, help="Path to smartctl saved files")
    parser.add_argument('-q', '--quiet', action='store_true', help="Be quiet about already labeled data")
    args = parser.parse_args()

    get_files(args.files, args.quiet)
