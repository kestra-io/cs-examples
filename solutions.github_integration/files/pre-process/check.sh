#!/bin/bash

# check for correct number of arguments
if [[ $# -ne 1 ]]; then
	echo "Usage: $0 /path/to/users.csv" >&2
	exit 1
fi

CSV_FILE="$1"
# check if the file exists
if [[ ! -f "$CSV_FILE" ]]; then
	echo "Error: file not found: $CSV_FILE" >&2
	exit 1
fi

# count how many data rows (excluding header) are in the CSV
total_lines=$(wc -l < "$CSV_FILE" | tr -d ' ')
if [[ "$total_lines" -le 1 ]]; then
	echo "No user rows found in $CSV_FILE"
	exit 0
fi

# print summary
data_rows=$(( total_lines - 1 ))
echo "File: $CSV_FILE"
echo "Total lines: $total_lines (including header)"
echo "User rows:  $data_rows"

echo
echo "Header row:"
head -n 1 "$CSV_FILE"
