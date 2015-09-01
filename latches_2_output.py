#! /usr/bin/env python2.7

from argparse import ArgumentParser
from re import match

import aiger_swig.aiger_wrap as aiglib


"""
Tool to convert 'latches' with specific names to corresponding AIGER signals.
"""

skippable = "[A-Za-z0-9_]*"
end = "\Z"
string_to_match = "(just(ice)?|bad|constr(aint)?|fair)_(var(iable)?|sig(nal)?)"
regex = "({skip}_)?{stm}(_{skip})?{end}".format(skip=skippable,
                                        stm=string_to_match,
                                        end=end)


def main(filename):
    model = aiglib.aiger_init()
    aiglib.aiger_open_and_read_from_file(model, filename)

    latches = model.latches

    for i in range(model.num_latches):
        latch = aiglib.get_aiger_symbol(latches, i)
        m = match(regex, latch.name)
        if m:
            ltype = m.groups()[1][0]
            if ltype == "b":
                aiglib.aiger_add_bad(model, latch.lit, latch.name)
            if ltype == "c":
                aiglib.aiger_add_constraint(model, latch.lit, latch.name)
            if ltype == "j":
                aiglib.aiger_add_justice(model, 1, [latch.lit], latch.name)
            if ltype == "f":
                aiglib.aiger_add_fairness(model, latch.lit, latch.name)


    res, string = aiglib.aiger_write_to_string(model,
                                               aiglib.aiger_ascii_mode,
                                               2147483648)

    assert res != 0, 'writing failure'

    print string


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument('aiger',
                        metavar='aiger',
                        nargs='?',
                        type=str,
                        default='/dev/stdin',
                        help='model synthesized in AIGER format')

    args = parser.parse_args()

    exit(main(args.aiger))
