# -*- coding: utf-8 -*-

import csv
import argparse
import os


def get_files(paths):
    results = []
    serials = set()
    errors = False

    try:
        for file in paths:
            file: str
            if os.path.isdir(file):
                for filename in os.listdir(file):
                    filename = file.rstrip('/') + '/' + filename
                    parse_file(filename, results, serials)
            elif os.path.isfile(file):
                parse_file(file, results, serials)
            else:
                print(f"{file} is not a file nor a directory")
                errors = True
    except KeyboardInterrupt:
        pass
    except EOFError:
        pass

    print(f"{serials} unique disks parsed, {results} labeled")

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


def parse_file(filename: str, results: list, serials: set):
    found = dict()
    errors = 0

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
            if "CCTF" in line:
                info_section = False
                data_section = False
                errors_section = True
                continue
            if info_section:
                if 'Model Family:  ' in line:
                    val = line.split('  ', 1)[1]
                    found["Model_Family"] = val.strip()

                if 'Serial Number' in line:
                    val = line.split('  ', 1)[1]
                    found["Serial_Number"] = val.strip()
                continue
            if data_section:
                for attr in attributes:
                    if attr in line:
                        val = line.split(" ")[-1].strip()
                        if attr == "Power_On_Hours":
                            found["Power_On_Hours_Exact"] = "false"
                            if 'h' in val:
                                val = val.split("h")[0]
                                found["Power_On_Hours_Exact"] = "true"
                        found[attr] = val.rstrip()
                continue
            if errors_section:
                if 'Error: UNC' in line:
                    errors += 1

    found["Errors_UNC"] = str(errors)

    if found["Serial_Number"] in serials:
        print(f"Skipping {found['Serial_Number']} in {filename}")
        return
    else:
        serials.add(found["Serial_Number"])

    for k in found:
        if k == "Power_On_Hours":
            print(f"{k}: {found[k]} ({int(found[k])/24:.2f} server days, {int(found[k])/8/304:.2f} office years)")
        else:
            print(f"{k}: {found[k]}")
    print(f"File is {filename}")

    answered = False
    while not answered:
        r = input("Is it OK, OLD, FAIL or discard? [K,O,F,X] ")
        r = r.lower()
        if r == 'k':
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
        elif r == 'x':
            answered = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Classify SMART data manually. Now.')
    parser.add_argument('files', nargs='+', type=str, help="Path to smartctl saved files")
    args = parser.parse_args()

    get_files(args.files)
