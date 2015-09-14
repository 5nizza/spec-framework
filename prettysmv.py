#! /usr/bin/env python3

from re import search as find
from python_ext import stripped_e
from str_aware_list import StrAwareList
from sys import stderr

indent_size = 2
tabs = False

def _prettify(stripped_lines: list):
    indent = " " * indent_size if not tabs else "\t"
    ret = StrAwareList()

    cur_i = 0
    in_b = False
    in_c = False
    define = False
    for i in range(len(stripped_lines)):
        line = stripped_lines[i]
        if line.startswith("MODULE"):
            ret += line
            cur_i = 1
            in_b = False
            n = False
        elif any(line.startswith(s) for s in ["VAR", "DEFINE", "ASSIGN", "INIT", "SYS_", "ENV_"]):
            if in_b:
                cur_i -= 1
            if n:
                cur_i -= 1
                n = False
            ret += indent * cur_i + line
            cur_i += 1
            in_b = True
        elif ":=" in line and not ";" in line:
            ret += indent * cur_i + line
            cur_i += 1
            define = True
        elif line.startswith("case"):
            in_c = True
            ret += indent * cur_i + line
            cur_i += 1
        elif "esac" in line:
            in_c = False
            cur_i -= 1
            ret += indent * cur_i + line
            if not in_c and not ":" in line and ";" in line:
                cur_i -= 1
        elif not in_c and not ":" in line and ";" in line:
            ret += indent * cur_i + line
            cur_i -= 1
        elif all(l.startswith("--") or not l for l in stripped_lines[i:len(stripped_lines)]):
            ret += line
        else:
            ret += indent * cur_i + line

    return str(ret)

def prettify(lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    return _prettify(stripped_e(lines))

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    g = parser.add_mutually_exclusive_group()

    g.add_argument("-t", "--tabs", help="use tabs instead of spaces", action="store_true")
    g.add_argument("-s", "--spaces", help="number of spaces", type=int, default=2)
    parser.add_argument("file")

    args = parser.parse_args()
    tabs = args.tabs
    indent_size = args.spaces

    with open(args.file) as fin:
        print(prettify(fin.readlines()))
