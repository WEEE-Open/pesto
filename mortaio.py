#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import argparse
import os


def main(directory: str):
    files = []
    col_names_set = set()
    col_names = []


    col_names_set.add("Brand")
    col_names.append("Brand")
    col_names_set.add("Model_Family")
    col_names.append("Model_Family")
    col_names_set.add("Serial_Number")
    col_names.append("Serial_Number")
    for filename in os.listdir(directory):
        fullpath = directory.rstrip('/') + '/' + filename
        if filename.startswith('labeled_') and filename.endswith('.csv') and filename != 'labeled_out.csv':
            print(f"Reading {filename}")
            files.append(fullpath)
            with open(fullpath, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
                for col in reader.fieldnames:
                    if col not in col_names_set:
                        col_names_set.add(col)
                        col_names.append(col)

    # Move to last
    col_names.remove("Status")
    col_names.append("Status")

    n = 0

    with open('labeled_out.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, fieldnames=col_names)
        writer.writeheader()

        for file in files:
            with open(file, 'r') as csvfile2:
                reader = csv.DictReader(csvfile2, delimiter=',', quotechar='"')
                for line in reader:
                    writer.writerow(line)
                    n += 1

    print(f"{n} rows processed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge csv files')
    parser.add_argument('dir', type=str, help="Path to directory full of csv files")
    args = parser.parse_args()

    main(args.dir)
