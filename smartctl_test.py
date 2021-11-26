#!/usr/bin/env python3

import sys
import utilites

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("Wrong arguments")
		exit(1)

	with open(sys.argv[1], 'r') as f:
		res = utilites.smartctl_get_status(utilites.parse_smartctl_output(f.read()))
		print(res)
