#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import argparse
import os
import traceback

from utilites import parse_smartctl_output, smartctl_get_status

RED = "\033[31;40m"
RED_REVERSE = "\033[41;30m"
GREEN_REVERSE = "\033[42;30m"
END_ESCAPE = "\033[0;0m"


def get_files(paths, quiet: bool, predict: bool):
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
                if 'Notsmart_Serial_Number' in row and 'Status' in row:
                    already_labeled[row['Notsmart_Serial_Number']] = row
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
            parse_file(filename, results, serials, counter, already_labeled, quiet, predict)
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


def parse_file(filename: str, results: list, serials: set, counter: int, already_labeled: dict, quiet: bool, predict: bool):
    print(f"File {counter} - {filename}")

    with open(filename, 'r') as f:
        found = parse_smartctl_output(f)
        found_at_least_one = False
        for k in found:
            if not k.startswith('Notsmart_'):
                found_at_least_one = True
                break

    prediction = None
    if predict:
        prediction = smartctl_get_status(found)

    if "Notsmart_Errors_UNC" in found:
        found["Notsmart_Errors_UNC"] = str(found["Notsmart_Errors_UNC"])

    if "Notsmart_Failing_Now" in found:
        found["Notsmart_Failing_Now"] = str(found["Notsmart_Failing_Now"])

    if "Notsmart_Serial_Number" not in found:
        found["Notsmart_Serial_Number"] = filename
    if found["Notsmart_Serial_Number"] in serials:
        print(f"Skipping duplicate {found['Notsmart_Serial_Number']}\n")
        return
    else:
        serials.add(found["Notsmart_Serial_Number"])

    if not found_at_least_one:
        print(f"Skipping empty disk\n")
        return

    if not quiet or not found['Notsmart_Serial_Number'] in already_labeled:
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
            if found[k].isnumeric() and int(found[k]) != 0 and k not in ("Notsmart_Serial_Number", "Notsmart_Rotation_Rate"):
                color1 = RED
                color2 = END_ESCAPE
            else:
                color1 = color2 = ""
            print(f"{k}: {color1}{found[k]}{color2}{details}")

    answered = False
    question = "Is it OK, SUS, OLD, FAIL or discard? [K,S,O,F,X] "

    if found['Notsmart_Serial_Number'] in already_labeled:
        old_labeled_row = already_labeled[found['Notsmart_Serial_Number']]
        print(f"{question}{old_labeled_row['Status']} (already labeled)")
        found['Status'] = old_labeled_row['Status']
        results.append(found)
        answered = True
        del already_labeled[found['Notsmart_Serial_Number']]

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
    if predict:
        prediction_formatted = "Unknown"
        if prediction is not None:
            prediction_formatted = prediction.upper()

        if prediction_formatted == found['Status']:
            comment = f"{GREEN_REVERSE}right :){END_ESCAPE}"
        else:
            comment = f"{RED_REVERSE}WRONG PREDICTION!{END_ESCAPE}"
        print(f"Predicted: {prediction_formatted} - {comment}")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Classify SMART data manually. Now.')
    parser.add_argument('files', nargs='+', type=str, help="Path to smartctl saved files")
    parser.add_argument('-q', '--quiet', action='store_true', help="Be quiet about already labeled data")
    parser.add_argument('-t', '--test', action='store_true', help="How am I mining?")
    args = parser.parse_args()

    get_files(args.files, args.quiet, args.test)
