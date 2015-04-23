#!/usr/bin/env python2.7


# The HWMCC/AIGER semantics of bad traces is
#   (inv U inv&err) | (G inv & GF fair)     [1]
#
# While we need to model check AIGER circuit against (good traces)
#   (~err W ~inv) & (G inv -> GF fair)
#
# which translates into the semantics of bad traces
#   (inv U inv&err) | (G inv & FG ~fair)    [2]
#
#
# We introduce new signal `new_fair` and use it instead of `fair` in [2],
# and reuse `inv`, `err`, (old)`fair`. Thus, the semantics of bad traces is:
#   (inv U inv&err) | (G inv & GF new_fair)
#
# Signal `new_fair` is defined as staying in the middle state of the automaton:
#   (start)   -aux->   (new_fair)   -fair->   (exit)
#     \/~aux              \/~fair               \/True
#
# In AIGER we introduce two latches: L2,L1.
# start = 00
# new_fair = 01
# exit = 11
#
# `aux` ---> |OR| --->|L1| -------> `before(aux)`        //aka 'exited the start state'
#             |             |
#             --<-----------
#
# `to_exit = before(aux) & fair`
# `to_exit` --->|OR| --->|L2| ------> `before(to_exit)`  //aka 'exited the new_fair state'
#                |             |
#                --<-----------
#
# To make `new_fair=01` hold, we need to receive `aux` and after that moment never received `fair`.
#
# AIGER for this:
#
# L1: OR1
# OR1: ~(~aux & ~L1)   -- AND1
#
# L2: OR2
# OR2: ~(~(L1 & fair) & ~L2)   -- two ANDs: AND2(internal) and AND3
#
# F = L2L1==01, thus F = ~L2 & L1

# Thus:
# L1: ~AND1
# L2: ~AND3
# F: AND4
# AND1: ~aux ~L1
# AND2: L1 & fair
# AND3: ~AND2 ~L2
# AND4: ~L2 L1
#


import argparse
import aiger_swig.aiger_wrap as aiglib


def _write_result(model):
    # aiglib.aiger_reencode(model)  # ic3-ref needs (?) 'right' order of indices of ANDs, etc.

    res, string = aiglib.aiger_write_to_string(model, aiglib.aiger_ascii_mode, 268435456)
    assert res != 0, 'writing failure'

    print string


def main(filename):
    #: :type: aiglib.aiger
    model = aiglib.aiger_init()
    aiglib.aiger_open_and_read_from_file(model, filename)

    if model.num_fairness == 0:
        _write_result(model)
        return

    assert model.num_fairness == 1

    next_lit = (model.maxvar + 1)*2

    # first, add all elements

    aiglib.aiger_add_input(model, next_lit, 'SYNT_2_HWMCC_aux')
    #: :type: aiglib.aiger_symbol
    aux = aiglib.get_aiger_symbol(model.inputs, model.num_inputs-1)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and1 = aiglib.get_aiger_and(model.ands, model.num_ands-1)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and2 = aiglib.get_aiger_and(model.ands, model.num_ands-1)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and3 = aiglib.get_aiger_and(model.ands, model.num_ands-1)
    next_lit += 2

    aiglib.aiger_add_and(model, next_lit, 1, 1)
    #: :type: aiglib.aiger_and
    and4 = aiglib.get_aiger_and(model.ands, model.num_ands-1)
    next_lit += 2

    aiglib.aiger_add_latch(model, next_lit, 1, 'SYNT_2_HWMCC_L1')
    #: :type: aiglib.aiger_and
    L1 = aiglib.get_aiger_symbol(model.latches, model.num_latches-1)
    next_lit += 2

    aiglib.aiger_add_latch(model, next_lit, 1, 'SYNT_2_HWMCC_L2')
    #: :type: aiglib.aiger_and
    L2 = aiglib.get_aiger_symbol(model.latches, model.num_latches-1)
    next_lit += 2

    #: :type: aiglib.aiger_symbol
    fair = model.fairness
    old_fair_lit = fair.lit

    # second, define all connections
    and1.rhs0, and1.rhs1 = aux.lit+1, L1.lit+1
    and2.rhs0, and2.rhs1 = L1.lit, old_fair_lit
    and3.rhs0, and3.rhs1 = and2.lhs+1, L2.lit+1
    and4.rhs0, and4.rhs1 = L2.lit+1, L1.lit

    L1.next = and1.lhs+1
    L2.next = and3.lhs+1

    fair.lit = and4.lhs

    #
    _write_result(model)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert AIGER (FG~fair) into GF(new_fair), not touching B and C. '
                                                 'Print the original model if no fair signals.')

    parser.add_argument('aiger',
                        metavar='aiger',
                        nargs='?',
                        type=str,
                        default='/dev/stdin',  #TODOfut: Works on Linux-like only
                        help='model synthesized in AIGER format')

    args = parser.parse_args()

    main(args.aiger)

    exit(0)
