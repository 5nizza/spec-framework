#!/usr/bin/env python3
import logging
import subprocess
import sys
import os
from python_ext import find, readfile
import argparse
from spec_2_smv import get_variables


def rename(l, inputs, outputs) -> str:
    # 'i1 cancel' becomes 'i1 cancel' if cancel is an input
    # 'i1 cancel' becomes 'i1 controllable_cancel' if cancel is an output
    signal = l.split()[1]
    if signal in inputs:
        return l
    else:
        return l.replace(signal, 'controllable_'+signal)


def main(smv_spec_file_name):
    logger = logging.getLogger(__name__)
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    spec_2_smv_path = scripts_dir + '/spec_2_smv.py'
    logger.debug('calling to %s' % spec_2_smv_path)

    # i could not fix the problem with unicode encodings when using execute_shell (with separate checks of exit statuses),
    # so use piping here instead
    aig = str(subprocess.check_output('%s %s | smvflatten | smvtoaig | aigtoaig -a' %
                                      (spec_2_smv_path, smv_spec_file_name),
                                      shell=True),
              encoding=sys.getdefaultencoding())

    inputs = get_variables('inputs', readfile(smv_spec_file_name).splitlines())
    outputs = get_variables('outputs', readfile(smv_spec_file_name).splitlines())

    lines = aig.splitlines()

    symbol_table_starts = find(lambda l: l.startswith('i'), lines)
    result = lines[:symbol_table_starts]

    i = symbol_table_starts
    while True:
        l = lines[i]
        if not l.startswith('i'):
            break

        result.append(rename(l, inputs, outputs))
        i += 1

    result += lines[i:]

    print('\n'.join(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Name me!')

    parser.add_argument('file', metavar='file',
                        type=argparse.FileType(),
                        help='input smv spec file')

    # parser.add_argument('--flag', action='store_true',
    #                     required=False, default=False,
    #                     help='some flag')

    args = parser.parse_args()
    exit(main(args.file.name))

