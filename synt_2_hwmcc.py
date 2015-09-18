#!/usr/bin/env python3

# The HWMCC/AIGER semantics of bad traces is
#   (inv U inv&err) | (G inv & GF just)     [1]
#
# While we need to model check AIGER circuit against (good traces)
#   (~err W ~inv) & (G inv -> GF just)
#
# which translates into the semantics of bad traces
#   (inv U inv&err) | (G inv & FG ~just)    [2]
#
#
# We introduce new signal `new_just` and use it instead of `just` in [2],
# and reuse `inv`, `err`, (old)`just`. Thus, the semantics of bad traces is:
#   (inv U inv&err) | (G inv & GF new_just)
#
# Signal `new_just` is defined as staying in the middle state of the automaton:
#   (start)   -aux->   (new_just)   -just->   (exit)
#     \/~aux              \/~just               \/True
#
# In AIGER we introduce two latches: L2,L1.
# start = 00
# new_just = 01
# exit = 11
#
# `aux` ---> |OR| --->|L1| -------> `before(aux)`        //aka 'exited the start state'
#             |             |
#             --<-----------
#
# `to_exit = before(aux) & just`
# `to_exit` --->|OR| --->|L2| ------> `before(to_exit)`  //aka 'exited the new_just state'
#                |             |
#                --<-----------
#
# To make `new_just=01` hold, we need to receive `aux` and after that moment never received `just`.
#
# AIGER for this:
#
# L1: OR1
# OR1: ~(~aux & ~L1)   -- AND1
#
# L2: OR2
# OR2: ~(~(L1 & just) & ~L2)   -- two ANDs: AND2(internal) and AND3
#
# F = L2L1==01, thus F = ~L2 & L1

# Thus:
# L1: ~AND1
# L2: ~AND3
# F: AND4
# AND1: ~aux ~L1
# AND2: L1 & just
# AND3: ~AND2 ~L2
# AND4: ~L2 L1
#


import argparse
import aiger_swig.aiger_wrap as aiglib


def _write_result(model):
    # aiglib.aiger_reencode(model)  # ic3-ref needs (?) 'right' order of indices of ANDs, etc.

    res, string = aiglib.aiger_write_to_string(model, aiglib.aiger_ascii_mode, 2147483648)

    assert res != 0, 'writing failure'

    print(string)


def main(filename):
    #: :type: aiglib.aiger
    model = aiglib.aiger_init()
    aiglib.aiger_open_and_read_from_file(model, filename)

    if model.num_justice == 0:
        _write_result(model)
        return

    assert model.num_justice == 1
    assert model.justice.size == 1

    next_lit = (model.maxvar + 1) * 2

    # first, add all elements

    aiglib.aiger_add_input(model, next_lit, 'SYNT_2_HWMCC_aux')
    #: :type: aiglib.aiger_symbol
    aux = aiglib.aiger_is_input(model, next_lit)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and1 = aiglib.aiger_is_and(model, next_lit)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and2 = aiglib.aiger_is_and(model, next_lit)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and3 = aiglib.aiger_is_and(model, next_lit)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and4 = aiglib.aiger_is_and(model, next_lit)
    next_lit += 2

    aiglib.aiger_add_latch(model, next_lit, 1, 'SYNT_2_HWMCC_L1')
    #: :type: aiglib.aiger_and
    L1 = aiglib.aiger_is_latch(model, next_lit)
    next_lit += 2

    aiglib.aiger_add_latch(model, next_lit, 1, 'SYNT_2_HWMCC_L2')
    #: :type: aiglib.aiger_and
    L2 = aiglib.aiger_is_latch(model, next_lit)
    next_lit += 2

    #: :type: aiglib.aiger_symbol
    old_just_lit = aiglib.get_justice_lit(model, 0, 0)

    # second, define all connections
    and1.rhs0, and1.rhs1 = aux.lit + 1, L1.lit + 1
    and2.rhs0, and2.rhs1 = L1.lit, old_just_lit
    and3.rhs0, and3.rhs1 = and2.lhs + 1, L2.lit + 1
    and4.rhs0, and4.rhs1 = L2.lit + 1, L1.lit

    L1.next = and1.lhs + 1
    L2.next = and3.lhs + 1

    aiglib.set_justice_lit(model, 0, 0, and4.lhs)

    #
    _write_result(model)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert from AIGER's FG(~just) into GF(new_just), not touching B and C. "
                                                 "Print the original model if no justice signals.")

    parser.add_argument('aiger',
                        metavar='aiger',
                        nargs='?',
                        type=str,
                        default='/dev/stdin',
                        help='model synthesized in AIGER format')

    args = parser.parse_args()

    main(args.aiger)

    exit(0)
