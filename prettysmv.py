#! /usr/bin/env python3

from python_ext import stripped
from str_aware_list import StrAwareList

indent_size = 2
tabs = False


def _prettify(stripped_lines:list):
    indent = " " * indent_size if not tabs else "\t"
    ret = StrAwareList()

    cur_i = 0
    in_b = False
    in_c = False
    for i, line in enumerate(stripped_lines):
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
        elif ":=" in line and ";" not in line:
            ret += indent * cur_i + line
            cur_i += 1
        elif line.startswith("case"):
            in_c = True
            ret += indent * cur_i + line
            cur_i += 1
        elif "esac" in line:
            in_c = False
            cur_i -= 1
            ret += indent * cur_i + line
            if not in_c and ":" not in line and ";" in line:
                cur_i -= 1
        elif not in_c and ":" not in line and ";" in line:
            ret += indent * cur_i + line
            cur_i -= 1
        elif all(l.startswith("--") or not l for l in stripped_lines[i:len(stripped_lines)]):
            ret += line
        else:
            ret += (indent * cur_i + line) if line else ''

    return str(ret)


def prettify(lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    return _prettify(stripped(lines))


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    g = parser.add_mutually_exclusive_group()

    parser.add_argument("-b", "--backup", type=str, metavar="SUFFIX",
                        help="back up original under SUFFIX, implies 'in-place'")
    parser.add_argument("-i", "--in-place", help="edit files in place", action="store_true")
    g.add_argument("-t", "--tabs", help="use tabs instead of spaces", action="store_true")
    g.add_argument("-s", "--spaces", help="number of spaces", type=int, default=2)
    parser.add_argument("file", nargs="+")

    args = parser.parse_args()
    tabs = args.tabs
    indent_size = args.spaces
    args.in_place |= args.backup is not None

    for f in args.file:
        with open(f) as fin:
            lines = fin.readlines()
        if args.in_place:
            if args.backup:
                with open(f + "." + args.backup, "w") as b:
                    b.write("".join(lines))
            with open(f, "w") as fout:
                print(prettify(lines), file=fout)
        else:
            print(prettify(lines))
