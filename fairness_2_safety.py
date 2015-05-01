#!/usr/bin/env python2.7

import argparse
import subprocess
import sys
import aiger_swig.aiger_wrap as aiglib


def execute_shell(cmd, input=''):
    """
    Execute cmd, send input to stdin.
    Return returncode, stdout, stderr.
    """

    proc_stdin = subprocess.PIPE if input != '' and input is not None else None
    proc_input = input if input != '' and input is not None else None

    # args = shlex.split(cmd)

    p = subprocess.Popen(cmd,
                         stdin=proc_stdin,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True)

    out, err = p.communicate(proc_input)

    return p.returncode, out, err


def to_str_ret_out_err(ret, out, err):
    res = ''
    res += "return:%i" % ret + '\n'
    res += "out:\n"
    res += out + '\n'
    res += "err:\n"
    res += err
    return res


def get_counter_aig(k):  # -> (int,int,int)
    template = \
        """
MODULE main  -- count-up till k
VAR
  state: 0..{k};
IVAR
  reset: boolean;

DEFINE
  beep := (state={k});

ASSIGN
  init(state) := 0;
  next(state) := case
                   reset: 0;
                   TRUE:state + 1;
                 esac;

SPEC
  AG(!beep)  -- then we use the bad signal
"""

    counter_smv = template.format(k=str(k))

    ret, out, err = execute_shell('smvflatten | smvtoaig | aigmove | aigstrip | aigtoaig -a', input=counter_smv)
    assert ret==0, to_str_ret_out_err(ret, out, err)

    out_lines = out.splitlines()
    aag, m, i, l, o, a = out_lines[0].split()
    assert i == '1' and o == '1'

    inp_signal = int(out_lines[1])

    out_def_line = out_lines[1 + 1 + int(l)]
    assert len(out_def_line.split()) == 1, out_def_line

    out_signal = int(out_def_line)

    return out, inp_signal, out_signal


def is_negated(l):
    return (l & 1) == 1


def negate(lit):
    return lit ^ 1


def strip_lit(l):
    return l & ~1


def get_lit_type(l):
    input_ = aiglib.aiger_is_input(spec, strip_lit(l))
    latch_ = aiglib.aiger_is_latch(spec, strip_lit(l))
    and_ = aiglib.aiger_is_and(spec, strip_lit(l))

    return input_, latch_, and_


#: :type: aiglib.aiger
spec = None
symbol_by_ulit = set()
counter_and_u_new_lits, counter_latch_u_new_lits = None, None
shift = None
out = None
new_format = None
#


def get_add_symbol(s_new_lit):
    assert counter_and_u_new_lits or counter_latch_u_new_lits, \
        'not initialized'

    u_new_lit = strip_lit(s_new_lit)

    if u_new_lit in symbol_by_ulit:
        input_, latch_, and_ = get_lit_type(u_new_lit)
        return input_ or latch_ or and_

    if u_new_lit == strip_lit(get_new_s_lit(2)):
        # previously input literal, it was not AND nor latch in the counter
        input_, latch_, and_ = get_lit_type(u_new_lit)
        return input_ or latch_ or and_

    assert u_new_lit in counter_and_u_new_lits or \
           u_new_lit in counter_latch_u_new_lits

    if u_new_lit in counter_and_u_new_lits:
        aiglib.aiger_add_and(spec, u_new_lit, 1, 1)
    else:  # u_new_lit in counter_latch_u_new_lits:
        aiglib.aiger_add_latch(spec, u_new_lit, 1, 'counter_latch')

    symbol_by_ulit.add(u_new_lit)
    input_, latch_, and_ = get_lit_type(u_new_lit)
    return input_ or latch_ or and_


def get_new_s_lit(old_lit):
    """ :return: _signed_ literal """
    # 2 is the input of a counter aig
    # 2 -> spec.fairness.lit, 3 -> negate(spec.fairness.lit)
    # counter_other_lit -> counter_other_lit + shift

    if strip_lit(old_lit) == 2:
        res = spec.fairness.lit
        if is_negated(old_lit):
            res = negate(res)
        return res

    # if strip_lit(old_lit) == strip_lit(counter_out_lit):
    #     res = new_counter_out_lit + shift
    #     if is_negated(old_lit):
    #         res = negate(res)
    #     return res

    return old_lit + shift

#
#    old_beep_lit = get_counter_aig_output_lit(counter_aig)
#    new_beep_lit = old_beep_lit + shift


def define_counter_new_lits(counter_aig):
    global counter_and_u_new_lits, counter_latch_u_new_lits
    counter_latch_u_new_lits = set()
    counter_and_u_new_lits = set()

    for l in counter_aig.splitlines()[2:]:  # ignore header and input
        tokens = l.split()

        if len(tokens) == 1:  # output, ignore
            continue
        if len(tokens) == 2:  # latch
            old_l = int(tokens[0])
            new_l = get_new_s_lit(old_l)
            counter_latch_u_new_lits.add(new_l)

        elif len(tokens) == 3:  # AND gate
            old_l = int(tokens[0])
            new_l = get_new_s_lit(old_l)
            counter_and_u_new_lits.add(new_l)

        else:
            assert 0, l


def define_shift():   # should go before any additions to the spec
    global shift
    next_lit = spec.maxvar*2 + 2
    # In counter_aig:
    # 2 is taken by the only input `reset`,
    # and 4 is the first used literal,
    # so in the new file: 4 should have value next_lit.
    shift = next_lit - 4


def add_counter_to_spec(k):
    counter_aig, inp_signal, out_signal = get_counter_aig(k)
    define_shift()
    define_counter_new_lits(counter_aig)

    for l in counter_aig.splitlines()[2:]:  # ignore header and input
        tokens = l.split()

        if len(tokens) == 1:  # output, ignore
            continue

        if len(tokens) == 2:  # latch
            old_l, old_next = int(tokens[0]), int(tokens[1])
            new_l, new_next = get_new_s_lit(old_l), get_new_s_lit(old_next)
            #: :type: aiglib.aiger_symbol
            l_symbol = get_add_symbol(new_l)
            get_add_symbol(new_next)
            l_symbol.next = new_next

        elif len(tokens) == 3:  # AND gate
            old_and, old_rhs0, old_rhs1 = int(tokens[0]), \
                                          int(tokens[1]), \
                                          int(tokens[2])
            new_and, new_rhs0, new_rhs1 = get_new_s_lit(old_and), \
                                          get_new_s_lit(old_rhs0), \
                                          get_new_s_lit(old_rhs1)
            #: :type: aiglib.aiger_and
            and_symbol = get_add_symbol(new_and)
            get_add_symbol(new_rhs0)
            get_add_symbol(new_rhs1)
            and_symbol.rhs0 = new_rhs0
            and_symbol.rhs1 = new_rhs1

            # print 'and: old_and, old_rhs0, old_rhs1 -> ' \
            #       'new_and, new_rhs0, new_rhs1', \
            #     old_and, old_rhs0, old_rhs1, \
            #     new_and, new_rhs0, new_rhs1
        else:
            assert 0, l

    # everything is already defined, and now goes
    aiglib.aiger_add_bad(spec, get_new_s_lit(out_signal), 'k-liveness')


def write_and_die():
    global spec, out, new_format
    res, string = aiglib.aiger_write_to_string(spec,
                                               aiglib.aiger_ascii_mode,
                                               2147483648)
    assert res != 0, 'writing failure'

    if not new_format:
        # post-process
        ret, out_string, err = execute_shell(
            'aigmove -i | aigor | aigtoaig -a',
            input=string)
        assert ret == 0, 'post-processing failure: ' + \
                         to_str_ret_out_err(ret, string, err) + \
                         'input was:\n' + string
        string = out_string

    out.write(string)
    exit(0)


def main(spec_filename, k):
    assert k>0, str(k)

    global spec
    #: :type: aiglib.aiger
    spec = aiglib.aiger_init()
    aiglib.aiger_open_and_read_from_file(spec, spec_filename)

    assert spec.num_justice == 0, 'justice is not supported, only fairness (TODO)'

    if spec.num_fairness == 0:
        write_and_die()

    add_counter_to_spec(k)
    # format to old-school?
    write_and_die()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert liveness into k-safety. '
                                                 'Requires: smvflatten, and aiger tools in your $PATH. '
                                                 'By default, the format is with the single bad output. ')

    parser.add_argument('aiger', metavar='aiger',
                        type=str,
                        help='input AIGER file to be transformed')

    parser.add_argument('out', metavar='out',
                        default=sys.stdout,
                        nargs='?',
                        type=argparse.FileType('w'),
                        help='output file name (default stdout)')

    parser.add_argument('-k', '--k', type=int, default=2,
                        help='(default 2) '
                             'Max value of the counter. Counting starts from 0.'
                             'This value will produce spec violation.')

    parser.add_argument('--new', '-n',
                        action='store_true',
                        default=False,
                        help='Produce new format (BCJF) -- '
                             'it adds new k-liveness Bad property '
                             'but it keeps the fair signal too.')

    args = parser.parse_args()

    out = args.out
    new_format = args.new

    exit(main(args.aiger, args.k))
