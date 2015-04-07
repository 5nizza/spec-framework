import xml.etree.ElementTree as ET
import sys

from sympy import true, sympify
from sympy.core.symbol import Symbol
from sympy.logic.boolalg import simplify_logic, false
from console_helpers import print_green


debug = True
log = True


def DBG_MSG(*args):
    if debug:
        print("[DBG]", *args, file=sys.stderr)


def LOG_MSG(s):
    if log:
        print("[LOG] " + str(s))


class Automaton:
    def __init__(self, states, init_state, acc_live_states, acc_dead_states, edges:'list of ((src,dst),set of labels) where label is a tuple of literals'):
        self.states = states
        self.init_state = init_state
        self.acc_live_states = acc_live_states
        self.acc_dead_states = acc_dead_states
        self.edges = edges

        assert self.acc_live_states or self.acc_dead_states

    def is_safety(self):
        return not self.acc_live_states

    def __str__(self):
        return 'states: %s, init_state: %s, acc_live_states: %s, acc_trap_states: %s, edges: %s' % \
            (self.states, self.init_state, self.acc_live_states, self.acc_dead_states, self.edges)


# def _remove_comments(automaton_str):
#     """
#     >>> print(_remove_comments("hi/**/"))
#     hi
#     >>> print(_remove_comments("hi/**/ih"))
#     hiih
#     >>> print(_remove_comments("1/**/2/*____*/3"))
#     123
#     """
#     cursor = 0
#     cleaned_automaton_str = ''
#
#     while True:
#         start_comment = automaton_str.find("/*", cursor)
#         if start_comment < 0:
#             cleaned_automaton_str += automaton_str[cursor:]
#             return cleaned_automaton_str
#
#         end_comment = automaton_str.find("*/", start_comment)
#         cleaned_automaton_str += automaton_str[cursor:start_comment]
#         cursor = end_comment+2
#
#
# def label_is_true(label:str):
#     if '(1)' in label:
#         return True
#
#     assert 0, 'current'
#
#
# def never_2_automaton(never_str) -> Automaton:  # TODO:AK: unit test
#     assert 'never' in never_str, 'not a promela never format: \n' + never_str
#
#     never_str = _remove_comments(never_str)
#
#     never_str = never_str.strip()
#     never_str = '\n'.join(never_str.splitlines()[1:-1]).strip()  # first line is 'never {', last line is '}'
#
#     states = set()
#     edges = dict()
#     acc_states = set()
#
#     transitions = [t for t in re.split(re.compile(";\n\}?\n?"), never_str) if t.strip()]
#     for t in transitions:
#         # split transition into head (state) and body (rules)
#
#         state_trans = stripped(t.split(":\n"))
#         assert len(state_trans) == 2, str(state_trans)
#         state, transitions_str = state_trans
#
#         if state.endswith('_init'):
#             init_state = state
#         if 'accept' in state:
#             acc_states.add(state)
#         states.add(state)
#
#         # transitions extraction
#         if re.match(re.compile("(.|\n)*skip(.|\n)*"), transitions_str):
#             edges[(state,state)] = "(1)"
#         elif not re.match(re.compile("(.|\n)*false(.|\n)*"), transitions_str):
#             l = re.split(re.compile("::"), transitions_str)
#             for y in l:
#                 if not re.match(re.compile("\s*if\s"), y):
#                     # fr = re.split(re.compile(" -> goto "), y)
#                     fr = stripped(y.split(" -> goto "))
#                     assert len(fr) == 2, str(fr)
#                     edgelab, rest_part = fr
#                     gre = re.split(re.compile("\s+f?i?"), rest_part)
#                     goto_state = gre[0]
#
#                     states.add(goto_state)
#
#                     if (state,goto_state) in edges:
#                         edges[(state,goto_state)] += "||" + edgelab
#                     else:
#                         edges[(state,goto_state)] = edgelab
#     print(edges)
#     acc_trap_states = set()
#     for s in acc_states:
#         if (s,s) in edges and label_is_true(edges[(s,s)]):   # TODO: very primitive, may not always work
#             acc_trap_states.add(s)
#
#     acc_states.difference_update(acc_trap_states)
#
#     print('acc_states', acc_states)
#     print('acc_trap_states', acc_trap_states)
#
#     return Automaton(states, init_state, acc_states, acc_trap_states, list(edges.items()))


def reduces_to_true(clauses):
    """
    >>> reduces_to_true([('True',), ('a',)])
    True
    >>> reduces_to_true([('r',), ('~r',)])
    True
    >>> reduces_to_true([('r',), ('~a',)])
    False
    >>> reduces_to_true([('r', 'b'), ('~r',)])
    False
    >>> reduces_to_true([('r','b'), ('~r','~b')])
    False
    >>> reduces_to_true(['a b'.split(), '~a ~b'.split(), '~a b'.split(), 'a ~b'.split()])
    True
    >>> reduces_to_true(['a b'.split(), '~a ~b'.split(), '~a b'.split(), 'a ~b'.split()])
    True
    """

    clauses = list(clauses)

    expr = false
    for c in clauses:
        new_c = true
        for l in c:
            v = l.replace('~', '')
            if v == 'True' or v == 'False':
                s = sympify(v)
            else:
                s = Symbol(v)
            new_c &= (~s if '~' in l else s)
        expr |= new_c

    return simplify_logic(expr) == true


def gff_2_automaton(gff_xml:str) -> Automaton:  # TODOopt: (boolean) simplify transitions labels
    # """
    # >>> print(gff_2_automaton(readfile('/tmp/tmp.gff')))
    # """
    states = set()
    edges = dict()  # (src,dst) -> set of labels
    root = ET.fromstring(gff_xml)
    for transition_element in root.iter('Transition'):
        src = transition_element.find('From').text
        dst = transition_element.find('To').text
        lbl = transition_element.find('Label').text

        states.add(src)
        states.add(dst)

        if (src,dst) not in edges:
            edges[(src,dst)] = set()

        edges[(src,dst)].add(tuple(lbl.split()))

    init_state = root.find('InitialStateSet').find('StateID').text

    acc_states = set(elem.text for elem in root.find('Acc').iter('StateID'))

    acc_trap_states = set()
    for s in acc_states:
        s_edges = edges.get((s,s))
        if s_edges:
            if reduces_to_true(s_edges):
                acc_trap_states.add(s)  # TODOopt: also replace edges with one trivial

    acc_states.difference_update(acc_trap_states)

    return Automaton(states, init_state, acc_states, acc_trap_states, list(edges.items()))
