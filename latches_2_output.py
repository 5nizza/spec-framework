#! /usr/bin/env python2.7

from argparse import ArgumentParser

import aiger_swig.aiger_wrap as aiglib


bad_names = ["bad_variable", "bad_var"]
constraint_names = ["constraint_variable", "constr_variable", "constraint_var", "constr_var"]
justice_names = ["justice_variable", "justice_var", "just_var", "just_variable"]
fair_names = ["fair_variable", "fair_var"]

def main(filename):
    model = aiglib.aiger_init()
    aiglib.aiger_open_and_read_from_file(model, filename)

    latches = model.latches
    latch = latches

    for i in range(model.num_latches):
        latch = aiglib.get_aiger_symbol(latches, i)
        if any(name in latch.name for name in bad_names):
            aiglib.aiger_add_bad(model, latch.lit, latch.name)
        if any(name in latch.name for name in constraint_names):
            aiglib.aiger_add_constraint(model, latch.lit, latch.name)
        if any(name in latch.name for name in justice_names):
            aiglib.aiger_add_justice(model, 1, [latches.lit], latch.name)
        if any(name in latch.name for name in fair_names):
            aiglib.aiger_add_fairness(model, latch.lit, latch.name)

    res, string = aiglib.aiger_write_to_string(model, aiglib.aiger_ascii_mode, 2147483648)

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
