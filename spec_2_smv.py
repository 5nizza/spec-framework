#!/usr/bin/env python3
import argparse
import copy
import re
from tempfile import NamedTemporaryFile
import os

import config
from common import setup_logging, reduces_to_true
from python_ext import readfile, stripped, find
from shell import execute_shell
from spec_parser import parse_smv
from str_aware_list import StrAwareList
from structs import Automaton, PropertySpec, SmvModule

from automata import automaton_from_spec


INVAR_SIGNAL_NAME = "invar_violated_signal"
BAD_SIGNAL_NAME = "bad_signal"
JUSTICE_SIGNAL_NAME = 'justice_signal'


def label2smvexpr(clauses: set):
    c_to_smv = lambda c: '(%s)' % ' & '.join(l.replace('~', '!') for l in c)
    smv_expr = '(%s)' % ' | '.join(map(c_to_smv, clauses))
    return smv_expr


def det_automaton_to_smv_module(automaton: Automaton, module_name: str, desc: str) -> SmvModule:
    """
    :return: smv module named `module_name`.
    The module defines (output) signals: `bad`, `fair`, `fall_out`.
    The transitions contain sink state to account for failing out of the automaton.
    In this case `fall_out` is true.
    Signal `bad` is true iff reach a dead state.
    Signal `fair` is true iff reach an accepting state and is_safety is False.
    The function assumes the automaton is determenistic.
    """

    logger.debug("automaton_to_smv_module: %s: %s: states %d, acc states: %d" %
                 (module_name,
                  ['liveness', 'safety'][automaton.is_safety],
                  len(automaton.states),
                  len(automaton.acc_states)))

    assert 'sink_state' not in automaton.states
    assert 'state' not in automaton.states

    template = """
MODULE {name}({signals})
VAR
  state : {{{enum_states}}};
DEFINE
  {bad_def}{fair_def}{fall_out}
INIT
  state = {init_state}
ASSIGN
  next(state) :=
  case
    {transitions}
  esac;
"""
    enum_states = ', '.join(automaton.states)
    enum_states += ', sink_state'

    transitions_list = []
    for ((u, v), clauses) in automaton.edges:
        transitions_list += ['state={u} & {lbl_expr} : {v};'.format(u=u, v=v, lbl_expr=label2smvexpr(clauses))]
    transitions_list.append('TRUE: sink_state;')
    transitions = '\n    '.join(transitions_list)

    bad_def = fair_def = ''
    if automaton.dead_states:
        bad_def = 'bad := %s;\n  ' % ' | '.join('(state=%s)' % s
                                                for s in automaton.dead_states)
    if not automaton.is_safety:
        fair_def = 'fair := %s;\n  ' % ' | '.join('(state=%s)' % s
                                                  for s in automaton.acc_states)

    fall_out = 'fall_out := (state=sink_state);'

    module_inputs = automaton.propositions  # NOTE: we do not check that user defined all propositions

    module_str = template.format(name=module_name,
                                 signals=', '.join(map(str, module_inputs)),
                                 init_state=automaton.init_state, enum_states=enum_states,
                                 transitions=transitions,
                                 bad_def=bad_def, fair_def=fair_def, fall_out=fall_out)

    return SmvModule(module_name, module_inputs, desc, module_str,
                     len(automaton.dead_states) > 0,
                     not automaton.is_safety)


def generate_name_for_property_module(spec: PropertySpec) -> str:
    res = 'module_%s' % re.sub('\W', '_', spec.desc)
    return res


def build_spec_module(spec: PropertySpec) -> SmvModule:
    automaton = automaton_from_spec(spec)

    name = generate_name_for_property_module(spec)
    smv_module = det_automaton_to_smv_module(automaton, name, spec.desc)

    return smv_module


def build_counting_fairness_module(nof_fair_signals: int, name: str) -> SmvModule:
    template = """
MODULE {name}({signals})
VAR
  state : {{{enum_states}}};
DEFINE
  {fair_def}
INIT
  state = {init_state}
ASSIGN
  next(state) :=
  case
    {transitions}
  esac;
"""
    init_state = 0

    nof_states = nof_fair_signals + 1
    enum_states = ', '.join(str(i) for i in range(nof_states))

    transitions = ['state=0: 1;']
    for s in range(1, nof_states):
        transitions.append('state=%s & fair%s: %s;' % (s, s, (s + 1) % nof_states))
    transitions.append('TRUE: state;')
    transitions = '\n    '.join(transitions)

    fair_def = 'fair := (state=0);'  # TODO: extract constant 'fair'

    signals = ('fair%s' % i for i in range(1, nof_fair_signals + 1))
    signals_str = ', '.join(signals)

    result = template.format(init_state=init_state, name=name,
                             signals=signals_str, enum_states=enum_states,
                             fair_def=fair_def, transitions=transitions)

    return SmvModule(name, signals, '', result, False, True)


def build_fairness_flag_module(nof_fair_signals: int, name: str) -> SmvModule:
    template = """
MODULE {name} ({signals})
VAR
  {flags}
ASSIGN
  {assignments}
DEFINE
  {fair_def}
"""

    signals = ("in{}".format(i) for i in range(nof_fair_signals))
    signals_str = ", ".join(signals)
    flags = "\n  ".join(["f{} : boolean;".format(i) for i in range(nof_fair_signals)])
    assignments = "\n  ".join(["next(f{i}) := (f{i} | in{i}) & !fair;".format(i=i) for i in range(nof_fair_signals)])
    fair_def = "fair := {};".format(" & ".join(["(f{i} | in{i})".format(i=i) for i in range(nof_fair_signals)]))

    result = template.format(name=name, assignments=assignments, signals=signals_str, flags=flags, fair_def=fair_def)
    return SmvModule(name, signals, '', result, False, True)


def compose_smv(non_spec_modules,
                asmpt_modules, grnt_modules,
                clean_main_module: SmvModule,
                counting_fairness_module: SmvModule,
                counting_justice_module: SmvModule) -> StrAwareList:
    smv = StrAwareList()

    for m in non_spec_modules:
        smv += m.module_str

    for am in asmpt_modules:
        smv += am.module_str

    for gm in grnt_modules:
        smv += gm.module_str

    if counting_fairness_module:
        smv += counting_fairness_module.module_str

    if counting_justice_module:
        smv += counting_justice_module.module_str

    # the main module
    smv += clean_main_module.module_str

    if asmpt_modules:
        smv += "VAR --assumptions modules"
        for m in asmpt_modules:
            smv += '  env_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))

        if counting_fairness_module:
            fair_signals = ['env_prop_%s.fair' % m.name
                            for m in filter(lambda m: m.has_fair, asmpt_modules)]
            smv += '  env_prop_%s : %s(%s);' % \
                   (counting_fairness_module.name,
                    counting_fairness_module.name,
                    ','.join(fair_signals))

        smv.sep()

    smv += "VAR --guarantees modules"
    for m in grnt_modules:
        smv += '  sys_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        assert m.has_bad or m.has_fair, str(m)

    if counting_justice_module:
        just_signals = ['sys_prop_%s.fair' % m.name
                        for m in filter(lambda m: m.has_fair, grnt_modules)]
        smv += '  sys_prop_%s : %s(%s);' % \
               (counting_justice_module.name,
                counting_justice_module.name,
                ','.join(just_signals))

    has_bad_sys = find(lambda m: m.has_bad, grnt_modules) != -1
    has_bad_env = find(lambda m: m.has_bad, asmpt_modules) != -1

    if any([has_bad_sys, has_bad_env, counting_fairness_module, counting_justice_module]):
        smv += "VAR"
        if has_bad_sys:
            smv += "  sys_prop_bad_variable: boolean;"

        if has_bad_env:
            smv += "  env_prop_constr_variable: boolean;"

        if counting_justice_module:
            smv += "  sys_prop_just_variable: boolean;"

        if counting_fairness_module:
            smv += "  env_prop_fair_variable: boolean;"
        smv.sep()

    smv += "ASSIGN"
    if has_bad_sys:
        smv += "  next(sys_prop_bad_variable) := %s;" % ' | '.join(['sys_prop_%s.bad' % m.name
                                                                    for m in filter(lambda m: m.has_bad, grnt_modules)])
        smv += "  init(sys_prop_bad_variable) := FALSE;"

    if has_bad_env:
        smv += "  next(env_prop_constr_variable) := !(%s);" % ' | '.join('env_prop_%s.bad' % m.name
                                                                         for m in filter(lambda m: m.has_bad, asmpt_modules))
        smv += "  init(env_prop_constr_variable) := TRUE;"

    if counting_fairness_module:
        smv += "  next(env_prop_fair_variable) := env_prop_%s.fair;" % counting_fairness_module.name
        smv += "  init(env_prop_fair_variable) := TRUE;"

    if counting_justice_module:
        smv += "  next(sys_prop_just_variable) := sys_prop_%s.fair;" % counting_justice_module.name
        smv += "  init(sys_prop_just_variable) := FALSE;"

    return smv


def main(smv_lines, base_dir):
    module_a_g_by_name = parse_smv(smv_lines, base_dir)

    name_d_a_g_records = tuple(filter(lambda n_d_a_g: len(n_d_a_g[1][1]) > 0 or len(n_d_a_g[1][2]) > 0,
                                      module_a_g_by_name.items()))

    assert len(name_d_a_g_records) == 1, "we support exactly one module with a specification" + str(name_d_a_g_records)

    name, (clean_main_module, assumptions, guarantees) = name_d_a_g_records[0]

    asmpt_modules = list(map(build_spec_module, assumptions))
    grnt_modules = list(map(build_spec_module, guarantees))

    non_spec_modules = tuple(map(lambda n_m_a_g: n_m_a_g[1][0],  # (name, (module,assumptions,guarantees))
                                 filter(lambda n_m_a_g: n_m_a_g[0] != name,
                                        module_a_g_by_name.items())))

    counting_justice_module = None
    counting_fairness_module = None
    nof_sys_live_modules = len(list(filter(lambda m: m.has_fair, grnt_modules)))
    nof_env_live_modules = len(list(filter(lambda m: m.has_fair, asmpt_modules)))
    if nof_sys_live_modules:
        counting_justice_module = build_fairness_flag_module(nof_sys_live_modules,
                                                             'counting_justice_' + name)
    if nof_env_live_modules:
        counting_fairness_module = build_fairness_flag_module(nof_env_live_modules,
                                                              'counting_fairness_' + name)

    # for m in asmpt_modules + grnt_modules:
    #     assert set(m.module_inputs).issubset(signals_and_macros)

    final_smv = compose_smv(non_spec_modules,
                            asmpt_modules,
                            grnt_modules,
                            clean_main_module,
                            counting_fairness_module,
                            counting_justice_module)

    print(str(final_smv))

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transforms spec SMV into valid SMV')

    parser.add_argument('-v', '--verbose', action='count', help='verbose output', default=-1)
    parser.add_argument('smv', metavar='smv',
                        type=argparse.FileType(),
                        help='input SMV file')

    args = parser.parse_args()

    logger = setup_logging(__name__, verbose_level=args.verbose)
    logger.info("run with args:%s", args)

    exit(main(args.smv.read().splitlines(),
              os.path.dirname(args.smv.name)))
