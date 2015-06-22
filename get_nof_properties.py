#!/usr/bin/env python

import sys


def get_nof_properties(hwmcc_model_file):
    with open(hwmcc_model_file) as infile:
        header = infile.readline()

    header_tokens = header.split()[1:]

    # return nof outputs + nof B + nof J + nof F
    # MILOABCJF
    # 0123456789
    res = int(header_tokens[3])
    if len(header_tokens) > 5:
        res += int(header_tokens[5])
    if len(header_tokens) > 7:
        res += int(header_tokens[7])
    if len(header_tokens) > 8:
        res += int(header_tokens[8])
    return res


if __name__ == "__main__":
    print get_nof_properties(sys.argv[1])
