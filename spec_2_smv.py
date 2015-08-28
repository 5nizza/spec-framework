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

    template = \
"""MODULE {name}({signals})
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

# def workaround_accept_init(never_str):
#     """
#     Handle the special case of an accepting initial state.
#       accept_init:
#       s0_init:
#     """
#     lines = never_str.splitlines()
#     index = find(lambda l: l.strip() == 'accept_init:', lines)
#     if index < 0:
#         return never_str
#
#     lines.pop(index)
#
#     line_with_init_state = lines[find(lambda l: 'init' in l, lines)]
#     tokens = line_with_init_state.split()
#     init_state = tokens[find(lambda t: 'init' in t, tokens)].strip(':').strip()
#
#     new_never_str = '\n'.join(lines)
#     new_never_str = new_never_str.replace(init_state, 'accept_init')
#
#     return new_never_str


# def gff_2_never(gff_str):
#     gff_tmp_file_name = never_file_name = None
#     try:
#         gff_tmp_file_name = get_tmp_file_name()
#         with open(gff_tmp_file_name, 'w') as f:
#             f.write(gff_str)
#
#         never_file_name = get_tmp_file_name()
#         goal_script = '$f = load -c GFF %s; save $f -c PROMELA %s;' % (gff_tmp_file_name, never_file_name)
#         execute_goal_script(goal_script)
#
#         never_str = readfile(never_file_name)
#
#     finally:
#         for n in [gff_tmp_file_name, never_file_name]:
#             if n:
#                 os.remove(n)
#
#     never_str = workaround_accept_init(never_str)
#
#     return never_str
# # from unittest import TestCase
# # class Test(TestCase):
# #     def test_(self):
# #         print(gff_2_never('<?xml version="1.0" encoding="UTF-8" standalone="no"?> <Structure label-on="Transition" type="FiniteStateAutomaton">     <Name/>     <Description/>     <Formula/>     <Alphabet type="Propositional">         <Proposition>init</Proposition>         <Proposition>read</Proposition>         <Proposition>readA</Proposition>         <Proposition>readB</Proposition>         <Proposition>valueT</Proposition>         <Proposition>write</Proposition>         <Proposition>writeA</Proposition>         <Proposition>writeB</Proposition>         <Proposition>writtenA</Proposition>         <Proposition>writtenB</Proposition>     </Alphabet>     <StateSet>         <State sid="11">             <Y>100</Y>             <X>380</X>             <Properties/>         </State>         <State sid="12">             <Y>100</Y>             <X>240</X>             <Properties/>         </State>         <State sid="15">             <Y>200</Y>             <X>140</X>             <Properties/>         </State>         <State sid="17">             <Y>300</Y>             <X>240</X>             <Properties/>         </State>         <State sid="19">             <Y>300</Y>             <X>380</X>             <Properties/>         </State>     </StateSet>     <InitialStateSet>         <StateID>15</StateID>     </InitialStateSet>     <TransitionSet complete="false">         <Transition tid="0">             <From>11</From>             <To>11</To>             <Label>True</Label>             <Properties/>         </Transition>         <Transition tid="1">             <From>12</From>             <To>12</To>             <Label>~writtenA ~writtenB</Label>             <Properties/>         </Transition>         <Transition tid="3">             <From>12</From>             <To>11</To>             <Label>readB</Label>             <Properties/>         </Transition>         <Transition tid="5">             <From>15</From>             <To>12</To>             <Label>writtenA</Label>             <Properties/>         </Transition>         <Transition tid="6">             <From>15</From>             <To>15</To>             <Label>True</Label>             <Properties/>         </Transition>         <Transition tid="8">             <From>17</From>             <To>17</To>             <Label>~writtenA ~writtenB</Label>             <Properties/>         </Transition>         <Transition tid="10">             <From>15</From>             <To>17</To>             <Label>writtenB</Label>             <Properties/>         </Transition>         <Transition tid="13">             <From>19</From>             <To>19</To>             <Label>True</Label>             <Properties/>         </Transition>         <Transition tid="14">             <From>17</From>             <To>19</To>             <Label>readA</Label>             <Properties/>         </Transition>     </TransitionSet>     <Acc type="Buchi">         <StateID>11</StateID>         <StateID>19</StateID>     </Acc>     <Properties/> </Structure> '))

def generate_name_for_property_module(spec: PropertySpec) -> str:
    res = 'module_%s' % re.sub('\W', '_', spec.desc)
    return res


def build_spec_module(spec: PropertySpec) -> SmvModule:
    automaton = automaton_from_spec(spec)

    name = generate_name_for_property_module(spec)
    smv_module = det_automaton_to_smv_module(automaton, name, spec.desc)

    return smv_module


def build_counting_fairness_module(nof_fair_signals: int, name: str) -> SmvModule:
    template = \
"""MODULE {name}({signals})
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


# def my_build_aggregate_module(module_name,
#                               asmpt_modules,
#                               grnt_modules,
#                               orig_clean_module:str,
#                               out:StrAwareList) -> (list, list, list):
#     module = StrAwareList()
#     module += orig_clean_module
#     module.sep()
#
#     if asmpt_modules:
#         module += "VAR --invariant modules"
#         for m in asmpt_modules:
#             assert set(m.module_inputs).issubset(signals_and_macros)
#             module += '  env_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
#         module.sep()
#
#     module += "VAR --spec modules"
#     for m in grnt_modules:
#         assert set(m.module_inputs).issubset(signals_and_macros)
#         module += '  sys_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
#         assert m.has_bad or m.has_fair, str(m)
#
#     module += "VAR --module that turns many liveness signals into the single one"
#     if counting_fairness_module:
#         fair_signals = ['sys_prop_%s.fair'%m.name for m in filter(lambda m: m.has_fair, sys_modules)]
#         module += '  sys_prop_%s : %s(%s);' % \
#                   (counting_fairness_module.name, counting_fairness_module.name, ','.join(fair_signals))
#
#     module.sep()
#
#     # assumptions
#     inv_violated_def = ' | '.join('env_prop_%s.fall_out' % m.name
#                                   for m in env_modules)
#     if introduce_signals_instead_of_sections:
#         module += "DEFINE"
#         module += '  {inv_signal_name} := ({inv_violated_def});'.format(
#             inv_signal_name=INVAR_SIGNAL_NAME,
#             inv_violated_def=inv_violated_def)
#     else:
#         module += "INVAR"
#         module += '  !(%s)' % inv_violated_def
#     module.sep()
#
#     # safety
#     bad_def = '(%s)' % ' | '.join('sys_prop_%s.bad' % m.name
#                                   for m in filter(lambda m: m.has_bad, sys_modules))
#     if introduce_signals_instead_of_sections:
#         module += 'DEFINE'
#         module += '  {bad_signal_name} := {bad_def};'.format(
#             bad_signal_name=BAD_SIGNAL_NAME,
#             bad_def=bad_def)
#     else:
#         if find(lambda m: m.has_bad, sys_modules) != -1:
#             module += "SPEC"
#             module += '  AG !(%s)' % bad_def
#             module.sep()
#
#     # liveness
#     if counting_fairness_module:
#         if introduce_signals_instead_of_sections:
#             module += "DEFINE"
#             module += '  {just_sig_name} := {just_sig_def};'.format(
#                 just_sig_name=JUSTICE_SIGNAL_NAME,
#                 just_sig_def='sys_prop_%s.fair' % counting_fairness_module.name)
#         else:
#             module += "FAIRNESS"
#             module += '  sys_prop_%s.fair' % counting_fairness_module.name
#
#         module.sep()
#
#     return module


# def build_aggregate_module(orig_clean_module:SmvModule,
#                            asmpt_modules,
#                            grnt_modules,
#                            signals_and_macros,
#                            counting_fairness_module:SmvModule,
#                            introduce_signals_instead_of_sections:bool) -> SmvModule:
#     """
#     :return: names for
#     (env_fall_out, env_bad, env_fair),
#     (sys_fall_out, sys_bad, sys_fair),
#     """
#     module = StrAwareList()
#     module += orig_clean_module
#     module.sep()
#
#     if asmpt_modules:
#         module += "VAR --invariant modules"
#         for m in asmpt_modules:
#             assert set(m.module_inputs).issubset(signals_and_macros)
#             module += '  env_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
#         module.sep()
#
#     module += "VAR --spec modules"
#     for m in grnt_modules:
#         assert set(m.module_inputs).issubset(signals_and_macros)
#         module += '  sys_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
#         assert m.has_bad or m.has_fair, str(m)
#
#     module += "VAR --module that turns many liveness signals into the single one"
#     if counting_fairness_module:
#         fair_signals = ['sys_prop_%s.fair'%m.name for m in filter(lambda m: m.has_fair, sys_modules)]
#         module += '  sys_prop_%s : %s(%s);' % \
#                   (counting_fairness_module.name, counting_fairness_module.name, ','.join(fair_signals))
#
#     module.sep()
#
#     # assumptions
#     inv_violated_def = ' | '.join('env_prop_%s.fall_out' % m.name
#                                   for m in env_modules)
#     if introduce_signals_instead_of_sections:
#         module += "DEFINE"
#         module += '  {inv_signal_name} := ({inv_violated_def});'.format(
#             inv_signal_name=INVAR_SIGNAL_NAME,
#             inv_violated_def=inv_violated_def)
#     else:
#         module += "INVAR"
#         module += '  !(%s)' % inv_violated_def
#     module.sep()
#
#     # safety
#     bad_def = '(%s)' % ' | '.join('sys_prop_%s.bad' % m.name
#                                   for m in filter(lambda m: m.has_bad, sys_modules))
#     if introduce_signals_instead_of_sections:
#         module += 'DEFINE'
#         module += '  {bad_signal_name} := {bad_def};'.format(
#             bad_signal_name=BAD_SIGNAL_NAME,
#             bad_def=bad_def)
#     else:
#         if find(lambda m: m.has_bad, sys_modules) != -1:
#             module += "SPEC"
#             module += '  AG !(%s)' % bad_def
#             module.sep()
#
#     # liveness
#     if counting_fairness_module:
#         if introduce_signals_instead_of_sections:
#             module += "DEFINE"
#             module += '  {just_sig_name} := {just_sig_def};'.format(
#                 just_sig_name=JUSTICE_SIGNAL_NAME,
#                 just_sig_def='sys_prop_%s.fair' % counting_fairness_module.name)
#         else:
#             module += "FAIRNESS"
#             module += '  sys_prop_%s.fair' % counting_fairness_module.name
#
#         module.sep()
#
#     return module


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
            # assert (not m.has_fair) and m.has_bad, str(m) + '\n Assumptions must be safety'

        if counting_fairness_module:
            fair_signals = ['sys_prop_%s.fair' % m.name
                            for m in filter(lambda m: m.has_fair, grnt_modules)]
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
        fair_signals = ['sys_prop_%s.fair' % m.name
                        for m in filter(lambda m: m.has_fair, grnt_modules)]
        smv += '  sys_prop_%s : %s(%s);' % \
               (counting_justice_module.name,
                counting_justice_module.name,
                ','.join(fair_signals))

    has_bad = any(m.has_bad for m in grnt_modules + asmpt_modules)
    smv.sep()
    if any([has_bad, counting_justice_module, counting_fairness_module]):
        smv += "VAR"
        if has_bad:
            smv += "  sys_prop_bad_variable: boolean;"
        # smv += "  constr_variable: boolean;"
        if counting_justice_module:
            smv += "  sys_prop_just_variable: boolean;"

        if counting_fairness_module:
            smv += "  env_prop_fair_variable: boolean;"
        smv.sep()

    smv += "ASSIGN"
    if has_bad:
        smv += "  next(sys_prop_bad_variable) := %s;"  % ' | '.join(['sys_prop_%s.bad' % m.name
                                                           for m in filter(lambda m: m.has_bad, grnt_modules)] +
                                                           ['env_prop_%s.bad' % m.name
                                                           for m in filter(lambda m: m.has_bad, asmpt_modules)])
        smv += "  init(sys_prop_bad_variable) := FALSE;"

    if counting_fairness_module:
        smv += "  next(env_prop_fair_variable) := env_prop_%s.fair;"  % counting_fairness_module.name
        smv += "  init(env_prop_fair_variable) := TRUE;"

    if counting_justice_module:
        smv += "  next(sys_prop_just_variable) := sys_prop_%s.fair;"  % counting_justice_module.name
        smv += "  init(sys_prop_just_variable) := FALSE;"

    return smv


# def my_main(smv_lines, base_dir):
#     module_a_g_by_name = parse_smv(smv_lines, base_dir)
#
#     aggregate_modules = list()
#     final_smv = StrAwareList()
#     fall_bad_fair_by_module = dict()
#
#     asmpt_bad_signals = list()
#
#     asmpt_fair_signals = list()
#     grnt_bad_signals = list()
#     grnt_fair_signals = list()
#
#     for name, (clean_module, assumptions, guarantees) in module_a_g_by_name.items():
#         asmpt_modules = [build_spec_module(a, a.signals + a.macros_signals)
#                          for a in assumptions]
#
#         asmpt_bad_signals.extend(filter(lambda m: m.has_bad, asmpt_modules))
#         asmpt_fair_signals.extend(filter(lambda m: m.has_bad, asmpt_modules))
#
#         grnt_modules = [build_spec_module(g, g.signals + g.macros_signals)
#                         for g in guarantees]
#
#         fall_bad_fair_by_module[name] = my_build_aggregate_module(name,
#                                                                   asmpt_modules,
#                                                                   grnt_modules,
#                                                                   clean_module,
#                                                                   final_smv)
#
#     modules_with_assumptions = tuple(filter(lambda m: m.has_assumptions, aggregate_modules))
#     modules_with_guarantees = tuple(filter(lambda m: m.has_bad or m.has_fair, aggregate_modules))
#     main_counting_fairness = len(tuple(filter(lambda m: m.has_fair, aggregate_modules)))
#     main_module = build_aggregate_module('main',
#                                          modules_with_assumptions, modules_with_guarantees,
#                                          orig_main_module,
#                                          main_counting_fairness,
#                                          False)
#
#     final_smv += main_module.module_str
#     print(final_smv.str())
#
#     return 0


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

    counting_fairness_module = None
    counting_justice_module = None
    nof_env_live_modules = len(list(filter(lambda m: m.has_fair, asmpt_modules)))
    nof_sys_live_modules = len(list(filter(lambda m: m.has_fair, grnt_modules)))
    if nof_env_live_modules:
        counting_fairness_module = build_counting_fairness_module(nof_env_live_modules,
                                                                  'counting_fairness_' + name)
    if nof_sys_live_modules:
        counting_justice_module = build_counting_fairness_module(nof_sys_live_modules,
                                                                 'counting_justice_' + name)

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

    parser.add_argument('smv', metavar='smv',
                        type=argparse.FileType(),
                        help='input SMV file')

    args = parser.parse_args()

    logger = setup_logging(__name__, verbose_level=1)
    logger.info("run with args:%s", args)

    exit(main(args.smv.read().splitlines(),
              os.path.dirname(args.smv.name)))
