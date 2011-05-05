import sys
import csv

from pprint import pprint

filename = sys.argv[1]

csv = csv.DictReader(open(filename))

columns = {}

INCLUDE_VALUES = False

for row in csv:
    empty_row = True
    for col, val in row.items():
        # change None to ''
        if val is None:
            val = ''
        # trim whitespace
        val = val.strip()
        if val != '':
            empty_row = False
    # skip rows with no values
    if empty_row:
        continue

    if INCLUDE_VALUES:
        for col, val in row.items():
            if not col in columns.keys():
                columns[col] = {}
            if not val in columns[col].keys():
                columns[col][val] = 0
            columns[col][val] += 1
    else:
        for col in row.keys():
            if not col in columns.keys():
                columns[col] = 0
            columns[col] += 1

pprint(columns)

