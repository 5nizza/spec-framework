import xml.etree.ElementTree as ET
import sys
import logging

from sympy import true, sympify
from sympy.core.symbol import Symbol
from sympy.logic.boolalg import simplify_logic, false


def setup_logging(logger_name):
    logging.basicConfig(format="%(asctime)-10s%(message)s",
                        datefmt="%H:%M:%S",
                        level=logging.DEBUG,
                        stream=sys.stderr)
    return logging.getLogger(logger_name)


class Automaton:
    def __init__(self, states, init_state, acc_live_states, acc_dead_states, edges:'list of ((src,dst),set of labels) where label is a tuple of literals'):
        self.states = states
        self.init_state = init_state
        self.acc_live_states = acc_live_states
        self.acc_dead_states = acc_dead_states
        self.edges = edges

        assert self.acc_live_states or self.acc_dead_states

    def is_safety(self):   # heuristics
        if are_all_states_accepting(self):
            return True
        return not self.acc_live_states

    def __str__(self):
        return 'states: %s, init_state: %s, acc_live_states: %s, acc_trap_states: %s, edges: %s' % \
            (self.states, self.init_state, self.acc_live_states, self.acc_dead_states, self.edges)


def are_all_states_accepting(automaton:Automaton):
    return set(automaton.states) == set(automaton.acc_live_states).union(automaton.acc_dead_states)


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
