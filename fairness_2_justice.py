#!/usr/bin/env python2.7

# We hack AIGER format and treat fairness as being SYSTEM guarantee,
# rather than as ENV assumption as in the original AIGER.
# This script (literally) removes the fairness signal and instead puts
# it into the justice signal.

import argparse
import sys


def main(aiger_lines):
    # MILOABCJF
    header_tokens = [s.strip() for s in aiger_lines[0].split()]
    if len(header_tokens) != 10:
        print('\n'.join(aiger_lines))
        return

    assert header_tokens[0] == 'aag', 'only ascii is supported'

    M, I, L, O, A, B, C, J, F = [int(s) for s in header_tokens[1:]]   # starting from 1 because `aig M I L O ..`

    if F == 0:
        print('\n'.join(aiger_lines))
        return

    assert F == 1, str(F)
    assert J == 0

    F_index = I + L + O + B + C
    F_lit = aiger_lines[F_index + 1]   # +1 for the header

    J = 1
    F = 0
    J_lines = ['1', str(F_lit)]

    aux_lines = ['aag %i %i %i %i %i %i %i %i %i' % (M, I, L, O, A, B, C, J, F)] + aiger_lines[1:F_index + 1] + J_lines + aiger_lines[F_index + 2:]

    # now fix the symbol table
    for i, l in enumerate(aux_lines):
        if l.startswith('f0'):
            break

    result_lines = aux_lines[:i] + ['j0 AIGER_JUSTICE_0'] + aux_lines[i + 1:]

    print('\n'.join(result_lines))
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FOR INTERNAL USE ONLY!')

    parser.add_argument('file', metavar='file',
                        type=argparse.FileType(),
                        nargs='?',
                        default=sys.stdin,
                        help='input file')

    args = parser.parse_args()

    aiger_lines = args.file.read().splitlines()

    exit(main(aiger_lines))
