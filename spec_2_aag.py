#!/usr/bin/env python3
import logging
import re
import subprocess
import sys
import os
import argparse
from nose.tools import assert_equal
from python_ext import find, readfile, stripped
from spec_parser import is_section_declaration



def get_controllable_var_section(smv_lines) -> list:
    controllable_var_lines = list()
    now_parsing = False
    for l in smv_lines:
        if now_parsing:
            if is_section_declaration(l):
                break
        if re.fullmatch('VAR *-- *controllable.*', l.strip()):
            now_parsing = True
        if now_parsing:
            controllable_var_lines.append(l)

    return controllable_var_lines


def get_controllable(smv_lines) -> set:
    controllable_var_section = get_controllable_var_section(smv_lines)

    variables = set()
    for l in controllable_var_section[1:]:  # first line is 'VAR --controllable'
        match = re.fullmatch('([\w_\.]+) *: *boolean.*', l.strip())
        if match:
            assert_equal(len(match.groups()), 1)
            variables.add(match.groups()[0])

    return variables


def rename(l, outputs) -> str:
    # 'i1 cancel' becomes 'i1 controllable_cancel' if cancel is an output
    signal = l.split()[1]
    if signal in outputs:
        return l.replace(signal, 'controllable_'+signal)
    else:
        return l


def main(smv_spec_file_name):
    logger = logging.getLogger(__name__)
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    spec_2_smv_path = scripts_dir + '/spec_2_smv.py'
    fairness_2_justice_path = scripts_dir + '/fairness_2_justice.py'
    logger.debug('calling to %s' % spec_2_smv_path)

    # i could not fix the problem with unicode encodings when using execute_shell (with separate checks of exit statuses),
    # so use piping here instead
    aig = str(subprocess.check_output('{spec_2_smv} {spec_file} | smvflatten | smvtoaig | aigtoaig -a | {fairness_2_justice}' \
                                      .format(spec_2_smv=spec_2_smv_path,
                                              spec_file=smv_spec_file_name,
                                              fairness_2_justice=fairness_2_justice_path),
                                      shell=True),
              encoding=sys.getdefaultencoding())

    inputs = get_controllable(readfile(smv_spec_file_name).splitlines())

    lines = aig.splitlines()

    symbol_table_starts = find(lambda l: l.startswith('i'), lines)
    result = lines[:symbol_table_starts]

    i = symbol_table_starts
    while True:
        l = lines[i]
        if not l.startswith('i'):
            break

        result.append(rename(l, inputs))
        i += 1

    result += lines[i:]

    print('\n'.join(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert specification '
                                                 'from the SYNT SMV format '
                                                 'into the SYNT AIGER format!')

    parser.add_argument('file', metavar='file',
                        type=argparse.FileType(),
                        help='input smv spec file')

    args = parser.parse_args()
    exit(main(args.file.name))

