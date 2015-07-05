#!/usr/bin/env python3
import argparse
import copy
from itertools import count
import re
from tempfile import NamedTemporaryFile
import os

import config
from common import Automaton, gff_2_automaton, are_all_states_accepting, setup_logging
from python_ext import readfile, stripped, find
from shell import execute_shell
from spec_parser import PropertySpec, parse_smv
from str_aware_list import StrAwareList


INVAR_SIGNAL_NAME = "invar_violated_signal"
BAD_SIGNAL_NAME = "bad_signal"
JUSTICE_SIGNAL_NAME = 'justice_signal'


def label2smvexpr(clauses:set):
    def c_to_smv(c):
        return '(%s)' % ' & '.join(l.replace('~', '!') for l in c)

    smv_expr = '(%s)' % ' | '.join(map(c_to_smv, clauses))
    return smv_expr


class SmvModule:
    def __init__(self, name, module_inputs, desc, module_str, has_bad, has_fair):
        self.module_inputs = tuple(module_inputs)
        self.name = name
        self.desc = desc
        self.module_str = module_str
        self.has_bad = has_bad
        self.has_fair = has_fair

    def __str__(self):
        return 'module: %s (%s), def:\n%s' %(self.name, self.desc, self.module_str)

    def fall_signals(self):
        assert 0
    def bad_signals(self):
        assert 0
    def fair_signals(self):
        assert 0


def det_automaton_to_smv_module(signals_and_macros, automaton:Automaton, module_name:str, desc:str) -> SmvModule:
    """
    :return: smv module named `module_name`.
    The module defines (output) signals: `bad`, `fair`, `fall_out`.
    The transitions contain sink state to account for failing out of the automaton.
      In this case `fall_out` is true.
    Signal `fair` is true iff reach an accepting non-sink state.
    Signal `bad` is true iff reach an accepting sink state.
    The function assumes the automaton is determenistic.
    """

    logger.debug("automaton_to_smv_module: %s has %d states, %d fair states, %d bad states" %
                 (module_name, len(automaton.states), len(automaton.acc_live_states), len(automaton.acc_dead_states)))

    assert 'sink_state' not in automaton.states
    assert 'state' not in automaton.states

    template = \
"""MODULE {name}({signals})
VAR
  state : {{{enum_states}}};
DEFINE
  {bad_def}
  {fair_def}
  {fall_out}
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
        transitions_list += ['state={u} & {lbl_expr} : {v};'.format(u=u,v=v, lbl_expr=label2smvexpr(clauses))]
    transitions_list.append('TRUE: sink_state;')
    transitions = '\n'.join(transitions_list)

    bad_def = fair_def = ''
    if automaton.acc_dead_states:
        bad_def = 'bad := %s;' % ' | '.join('(state=%s)' % s for s in automaton.acc_dead_states)
    if automaton.acc_live_states:
        fair_def = 'fair := %s;' % ' | '.join('(state=%s)' % s for s in automaton.acc_live_states)

    fall_out = 'fall_out := (state=sink_state);'

    module_str = template.format(name=module_name,
                                 signals=', '.join(map(str, signals_and_macros)),
                                 init_state=automaton.init_state, enum_states=enum_states,
                                 transitions=transitions,
                                 bad_def=bad_def, fair_def=fair_def, fall_out=fall_out)

    return SmvModule(module_name, signals_and_macros, desc, module_str,
                     len(automaton.acc_dead_states)>0,
                     len(automaton.acc_live_states)>0)


def get_guarded_block(guard_comment:str, smv_lines) -> list:
    block_start = find(lambda l: ('<%s>' % guard_comment) in l, smv_lines)
    block_end = find(lambda l: ('</%s>' % guard_comment) in l, smv_lines)
    return smv_lines[block_start:block_end+1]


def get_variables(vars_comment, smv_lines) -> list:
    vars_block = get_guarded_block(vars_comment, smv_lines)
    stripped_lines = stripped(vars_block)

    variables = set()
    for l in filter(lambda l: ':' in l, stripped_lines):
        variables.add(l.split(':')[0].strip())

    return variables


def get_tmp_file_name():
    tmp = NamedTemporaryFile(prefix='spec2smv_', delete=False)
    return tmp.name


def execute_goal_script(script:str) -> str:
    """
    :return: stdout as printed by GOAL
    """
    script_tmp_file_name = get_tmp_file_name()
    with open(script_tmp_file_name, 'w') as f:
        f.write(script)
        logger.debug(script)
    
    cmd_to_execute = '%s batch %s' % (config.GOAL, script_tmp_file_name)
    res, out, err = execute_shell(cmd_to_execute)
    assert res == 0 and err == '', 'Shell call failed:\n' + cmd_to_execute + '\nres=%i\n err=%s' % (res, err)

    os.remove(script_tmp_file_name)
    return out


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


def formula_2_automaton_gff(spec:PropertySpec) -> PropertySpec:
    input_file_name = get_tmp_file_name()
    output_file_name = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(spec.data)

    goal_script = "translate QPTL -m ltl2ba -t nbw -o %s %s;" % (output_file_name, input_file_name)
    execute_goal_script(goal_script)

    automaton_data = readfile(output_file_name)

    new_spec = copy.copy(spec)
    new_spec.data = automaton_data
    new_spec.input_type = "automaton"

    os.remove(input_file_name)
    os.remove(output_file_name)

    return new_spec


def is_liveness(raw_gff:str):
    automaton = gff_2_automaton(raw_gff)
    return not automaton.is_safety()


def minimize_acc_gff(raw_gff:str) -> str:  # TODO: possible to get rid of all these tmp files in other places?
    logger.debug('minimize_acc_gff')

    input_file_name = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(raw_gff)

    result_gff = execute_goal_script("acc -min {inp};".format(inp=input_file_name))  # TODO: better stack all the commands and then execute them at once
    assert result_gff

    os.remove(input_file_name)
    return result_gff


def simplify_gff(raw_gff:str) -> str:
    logger.info('simplifying')

    input_file_name = get_tmp_file_name()
    output_file_name = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(raw_gff)

    execute_goal_script("simplify -m simulation -dse -ds -rse -rs -ru -rd -o {out} {inp};".format(out=output_file_name, inp=input_file_name))
    res = readfile(output_file_name)

    os.remove(input_file_name)
    os.remove(output_file_name)

    return res


def complement_gff(raw_gff:str) -> str:
    logger.info('complementing')

    input_file_name = get_tmp_file_name()
    output_file_name = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(raw_gff)

    execute_goal_script("complement -o {out} {inp};".format(out=output_file_name, inp=input_file_name))

    res = readfile(output_file_name)

    os.remove(input_file_name)
    os.remove(output_file_name)

    return res


def determenize_gff(raw_gff:str) -> str:   # TODO: handle the case of non-deterministic automata
    """ Assumes that the determinization is possible. """
    logger.info('determinizing')

    # TODOopt: don't use files
    input_file_name = get_tmp_file_name()
    output_file_name = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(raw_gff)

    execute_goal_script("determinization -m bk09 -o {out} {inp};".format(out=output_file_name,
                                                                         inp=input_file_name))
    res = readfile(output_file_name)

    os.remove(input_file_name)
    os.remove(output_file_name)

    return res


def build_automaton(spec:PropertySpec) -> Automaton:
    """
    All automata are 'positive' deterministic Buchi automata,
    (we complement negated ones).
    """

    logger.info('build_automaton for spec: %s', spec.desc)

    assert spec.is_automaton, 'other input types are not supported'

    gff = spec.data

    input_file_name = get_tmp_file_name()
    output_file_name = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(gff)

    complement_stmnt = ''
    if not spec.is_positive:
        complement_stmnt = '$res = complement $res;'

    # Minimizing the accepting set:
    # 1) to make naive safety detection (in later steps) work,
    # 2) should also help to reduce the max value of liveness counters and their number (if any)

    goal_script = """
$res = open "{input_file_name}";
{complement_stmnt}
$res = determinization -m bk09 $res;
$res = simplify -m fair -dse -ds -rse -rs -ru -rd $res;
acc -min $res;
save $res {output_file_name};
""".format(complement_stmnt=complement_stmnt,
           input_file_name=input_file_name,
           output_file_name=output_file_name)

    execute_goal_script(goal_script)

    gff = readfile(output_file_name)

    os.remove(input_file_name)
    os.remove(output_file_name)

    automaton = gff_2_automaton(gff)

    if automaton.is_safety():
        assert are_all_states_accepting(automaton), str(automaton)

    logger.info('after all manipulations: %s', ['liveness', 'safety'][automaton.is_safety()])

    return automaton
    # if not spec.is_guarantee:
    #     assert spec.is_positive, 'currently: assumptions must be positive'  # TODOfut: support for safety bad traces
    # else:
    #     if is_liveness(gff):
    #         logger.info('LIVENESS automaton!')
    #         if not spec.is_positive:
    #             gff = complement_gff(gff)
    #     else:
    #         logger.info('SAFETY automaton!')
    #         # we could also support good traces by complementing the input automaton,
    #         # but this can explode (in # of states, but unlikely comput expensive),
    #         # and we want to keep the original encoding (which is likely consice)
    #         assert not spec.is_positive, 'safety only as bad traces is supported'

    # gff = minimize_acc_gff(simplify_gff(determenize_gff(gff)))
    # TODOopt: try minimize_acc(simplify(minimize_acc(determenize(..)))


def generate_name_for_spec(spec:PropertySpec) -> str:
    res = 'spec_%s' % re.sub('\W', '_', spec.desc)
    return res


def build_spec_module(spec:PropertySpec, signals_and_macros) -> SmvModule:
    assert 0, 'call strip somewhere'
    automaton = build_automaton(spec)

    name = generate_name_for_spec(spec)
    smv_module = det_automaton_to_smv_module(signals_and_macros, automaton, name, spec.desc)

    return smv_module


def build_counting_fairness_module(nof_fair_signals:int, name:str) -> SmvModule:
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
    for s in range(1,nof_states):
        transitions.append('state=%s & fair%s: %s;' % (s,s,(s+1)%nof_states))
    transitions.append('TRUE: state;')
    transitions = '\n'.join(transitions)

    fair_def = 'fair := (state=0);'  # TODO: extract constant 'fair'

    signals = ('fair%s'%i for i in range(1, nof_fair_signals+1))
    signals_str = ', '.join(signals)

    result = template.format(init_state=init_state, name=name,
                             signals=signals_str, enum_states=enum_states,
                             fair_def=fair_def, transitions=transitions)

    return SmvModule(name, signals, '', result, False, True)


def my_build_aggregate_module(module_name,
                              asmpt_modules,
                              grnt_modules,
                              orig_clean_module:str,
                              out:StrAwareList) -> (list, list, list):
    module = StrAwareList()
    module += orig_clean_module
    module.sep()

    if asmpt_modules:
        module += "VAR --invariant modules"
        for m in asmpt_modules:
            assert set(m.module_inputs).issubset(signals_and_macros)
            module += '  env_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        module.sep()

    module += "VAR --spec modules"
    for m in grnt_modules:
        assert set(m.module_inputs).issubset(signals_and_macros)
        module += '  sys_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        assert m.has_bad or m.has_fair, str(m)

    module += "VAR --module that turns many liveness signals into the single one"
    if counting_fairness_module:
        fair_signals = ['sys_prop_%s.fair'%m.name for m in filter(lambda m: m.has_fair, sys_modules)]
        module += '  sys_prop_%s : %s(%s);' % \
                  (counting_fairness_module.name, counting_fairness_module.name, ','.join(fair_signals))

    module.sep()

    # assumptions
    inv_violated_def = ' | '.join('env_prop_%s.fall_out' % m.name
                                  for m in env_modules)
    if introduce_signals_instead_of_sections:
        module += "DEFINE"
        module += '  {inv_signal_name} := ({inv_violated_def});'.format(
            inv_signal_name=INVAR_SIGNAL_NAME,
            inv_violated_def=inv_violated_def)
    else:
        module += "INVAR"
        module += '  !(%s)' % inv_violated_def
    module.sep()

    # safety
    bad_def = '(%s)' % ' | '.join('sys_prop_%s.bad' % m.name
                                  for m in filter(lambda m: m.has_bad, sys_modules))
    if introduce_signals_instead_of_sections:
        module += 'DEFINE'
        module += '  {bad_signal_name} := {bad_def};'.format(
            bad_signal_name=BAD_SIGNAL_NAME,
            bad_def=bad_def)
    else:
        if find(lambda m: m.has_bad, sys_modules) != -1:
            module += "SPEC"
            module += '  AG !(%s)' % bad_def
            module.sep()

    # liveness
    if counting_fairness_module:
        if introduce_signals_instead_of_sections:
            module += "DEFINE"
            module += '  {just_sig_name} := {just_sig_def};'.format(
                just_sig_name=JUSTICE_SIGNAL_NAME,
                just_sig_def='sys_prop_%s.fair' % counting_fairness_module.name)
        else:
            module += "FAIRNESS"
            module += '  sys_prop_%s.fair' % counting_fairness_module.name

        module.sep()

    return module


def build_main_aggregate_module():
    pass
    CURRENT: we need to track all object instances
             of types that contain a spec inside???


def build_main_module(clean_main_module:SmvModule, sub_modules) -> SmvModule:
    module_str = StrAwareList()




def build_aggregate_module(orig_clean_module:SmvModule,
                           asmpt_modules,
                           grnt_modules,
                           signals_and_macros,
                           counting_fairness_module:SmvModule,
                           introduce_signals_instead_of_sections:bool) -> SmvModule:
    """
    :return: names for
    (env_fall_out, env_bad, env_fair),
    (sys_fall_out, sys_bad, sys_fair),
    """
    module = StrAwareList()
    module += orig_clean_module
    module.sep()

    if asmpt_modules:
        module += "VAR --invariant modules"
        for m in asmpt_modules:
            assert set(m.module_inputs).issubset(signals_and_macros)
            module += '  env_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        module.sep()

    module += "VAR --spec modules"
    for m in grnt_modules:
        assert set(m.module_inputs).issubset(signals_and_macros)
        module += '  sys_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        assert m.has_bad or m.has_fair, str(m)

    module += "VAR --module that turns many liveness signals into the single one"
    if counting_fairness_module:
        fair_signals = ['sys_prop_%s.fair'%m.name for m in filter(lambda m: m.has_fair, sys_modules)]
        module += '  sys_prop_%s : %s(%s);' % \
                  (counting_fairness_module.name, counting_fairness_module.name, ','.join(fair_signals))

    module.sep()

    # assumptions
    inv_violated_def = ' | '.join('env_prop_%s.fall_out' % m.name
                                  for m in env_modules)
    if introduce_signals_instead_of_sections:
        module += "DEFINE"
        module += '  {inv_signal_name} := ({inv_violated_def});'.format(
            inv_signal_name=INVAR_SIGNAL_NAME,
            inv_violated_def=inv_violated_def)
    else:
        module += "INVAR"
        module += '  !(%s)' % inv_violated_def
    module.sep()

    # safety
    bad_def = '(%s)' % ' | '.join('sys_prop_%s.bad' % m.name
                                  for m in filter(lambda m: m.has_bad, sys_modules))
    if introduce_signals_instead_of_sections:
        module += 'DEFINE'
        module += '  {bad_signal_name} := {bad_def};'.format(
            bad_signal_name=BAD_SIGNAL_NAME,
            bad_def=bad_def)
    else:
        if find(lambda m: m.has_bad, sys_modules) != -1:
            module += "SPEC"
            module += '  AG !(%s)' % bad_def
            module.sep()

    # liveness
    if counting_fairness_module:
        if introduce_signals_instead_of_sections:
            module += "DEFINE"
            module += '  {just_sig_name} := {just_sig_def};'.format(
                just_sig_name=JUSTICE_SIGNAL_NAME,
                just_sig_def='sys_prop_%s.fair' % counting_fairness_module.name)
        else:
            module += "FAIRNESS"
            module += '  sys_prop_%s.fair' % counting_fairness_module.name

        module.sep()

    return module


def build_main_module(env_modules, sys_modules,
                      user_main_module:str,
                      signals_and_macros,
                      counting_fairness_module:SmvModule) -> StrAwareList:
    main_module = StrAwareList()
    main_module += user_main_module
    main_module.sep()

    if env_modules:
        main_module += "VAR --invariant modules"
        for m in env_modules:
            assert set(m.module_inputs).issubset(signals_and_macros)
            main_module += '  env_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        main_module.sep()

        main_module += "INVAR"
        main_module += '  !(%s)' % ' | '.join('env_prop_%s.fall_out' % m.name for m in env_modules)  # 'bad' and 'fair' do not matter for inv
        main_module.sep()

    main_module += "VAR --spec modules"
    for m in sys_modules:
        assert set(m.module_inputs).issubset(signals_and_macros)
        main_module += '  sys_prop_%s : %s(%s);' % (m.name, m.name, ','.join(m.module_inputs))
        assert m.has_bad or m.has_fair, str(m)

    if counting_fairness_module:
        fair_signals = ['sys_prop_%s.fair'%m.name for m in filter(lambda m: m.has_fair, sys_modules)]
        main_module += '  sys_prop_%s : %s(%s);' % \
                       (counting_fairness_module.name, counting_fairness_module.name, ','.join(fair_signals))
    main_module.sep()

    if find(lambda m: m.has_bad, sys_modules) != -1:
        main_module += "SPEC"
        main_module += '  AG !(%s)' % ' | '.join('sys_prop_%s.bad' % m.name
                                                 for m in filter(lambda m: m.has_bad, sys_modules))
        main_module.sep()

    if counting_fairness_module:
        main_module += "FAIRNESS"
        main_module += '  sys_prop_%s.fair' % counting_fairness_module.name

    return main_module


def strip_unused_symbols(spec_property:PropertySpec):  # GOAL may produce automaton
                                                       # whose alphabet contains symbols
                                                       # not used in any transition labels
                                                       # here we remove unused propositions
                                                       # from the alphabet
    lines = spec_property.data.splitlines()

    alphabet_start = find(lambda l: '<Alphabet' in l, lines)
    alphabet_end = find(lambda l: '</Alphabet' in l, lines)

    if alphabet_start == -1 or alphabet_end == -1:
        return spec_property

    trans_start = find(lambda l: '<TransitionSet' in l, lines)
    trans_end = find(lambda l: '</TransitionsSet' in l, lines)

    lbl_lines = list(filter(lambda l: '<Label' in l, lines[trans_start+1:trans_end]))

    used_labels = set()
    for lbl_line in lbl_lines:
        # <Label>~g ~r</Label>
        #: :type: str
        lbls = lbl_line[lbl_line.find('>')+1 : lbl_line.find('<', lbl_line.find('>'))]
        lbls = stripped(lbls.replace('~', '').split())
        used_labels.update(lbls)

    #: :type: list
    result = lines[:alphabet_start+1]
    for lbl in filter(lambda l: l!='True', used_labels):
        result.append("        <Proposition>%s</Proposition>" % lbl)

    result += lines[alphabet_end:]

    spec_property.data = '\n'.join(result)


def my_main(smv_lines, base_dir):
    module_a_g_by_name = parse_smv(smv_lines, base_dir)

    aggregate_modules = list()
    final_smv = StrAwareList()
    fall_bad_fair_by_module = dict()

    asmpt_bad_signals = list()

    asmpt_fair_signals = list()
    grnt_bad_signals = list()
    grnt_fair_signals = list()

    for name, (clean_module, assumptions, guarantees) in module_a_g_by_name.items():
        # for p in spec.properties:  # TODO
        #     strip_unused_symbols(p)

        asmpt_modules = [build_spec_module(a, a.signals + a.macros_signals)
                         for a in assumptions]

        asmpt_bad_signals.extend(filter(lambda m: m.has_bad, asmpt_modules))
        asmpt_fair_signals.extend(filter(lambda m: m.has_bad, asmpt_modules))

        grnt_modules = [build_spec_module(g, g.signals + g.macros_signals)
                        for g in guarantees]

        fall_bad_fair_by_module[name] = my_build_aggregate_module(name,
                                                                  asmpt_modules,
                                                                  grnt_modules,
                                                                  clean_module,
                                                                  final_smv)

    modules_with_assumptions = tuple(filter(lambda m: m.has_assumptions, aggregate_modules))
    modules_with_guarantees = tuple(filter(lambda m: m.has_bad or m.has_fair, aggregate_modules))
    main_counting_fairness = len(tuple(filter(lambda m: m.has_fair, aggregate_modules)))
    main_module = build_aggregate_module('main',
                                         modules_with_assumptions, modules_with_guarantees,
                                         orig_main_module,
                                         main_counting_fairness,
                                         False)

    final_smv += main_module.module_str
    print(final_smv.str())

    return 0


def main(smv_lines, base_dir):
    module_a_g_by_name = parse_smv(smv_lines, base_dir)

    aggregate_modules = list()
    final_smv = StrAwareList()
    for name, (clean_module, assumptions, guarantees) in module_a_g_by_name.items():
        # for p in spec.properties:  # TODO
        #     strip_unused_symbols(p)

        asmpt_modules = [build_spec_module(a, a.signals + a.macros_signals)
                         for a in assumptions]
        grnt_modules = [build_spec_module(g, g.signals + g.macros_signals)
                        for g in guarantees]

        final_smv += ['-- %s\n' % (s.name + s.desc) + s.module_str
                      for s in grnt_modules + asmpt_modules]
        final_smv.sep()

        counting_justice_module = None
        nof_sys_live_modules = len(list(filter(lambda m: m.has_fair, grnt_modules)))
        if nof_sys_live_modules:
            counting_justice_module = build_counting_fairness_module(nof_sys_live_modules,
                                                                     'counting_justice_'+name)
            final_smv += counting_justice_module.module_str

        aggregate_module = build_aggregate_module(name,
                                                  asmpt_modules, grnt_modules,
                                                  clean_module,
                                                  counting_justice_module,
                                                  True)

        final_smv += aggregate_module.module_str

        aggregate_modules.append(final_smv)

    modules_with_assumptions = tuple(filter(lambda m: m.has_assumptions, aggregate_modules))
    modules_with_guarantees = tuple(filter(lambda m: m.has_bad or m.has_fair, aggregate_modules))
    main_counting_fairness = len(tuple(filter(lambda m: m.has_fair, aggregate_modules)))
    main_module = build_aggregate_module('main',
                                         modules_with_assumptions, modules_with_guarantees,
                                         orig_main_module,
                                         main_counting_fairness,
                                         False)

    final_smv += main_module.module_str
    print(final_smv.str())

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transforms spec SMV into valid SMV')

    parser.add_argument('smv', metavar='smv',
                        type=argparse.FileType(),
                        help='input SMV file')

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("run with args:%s", args)

    exit(main(args.smv.read().splitlines(),
              os.path.dirname(args.smv.name)))
