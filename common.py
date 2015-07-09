from functools import lru_cache
import xml.etree.ElementTree as ET
import sys
import logging

from sympy import true, sympify
from sympy.core.symbol import Symbol
from sympy.logic.boolalg import simplify_logic, false
from ansistrm import ColorizingStreamHandler


def setup_logging(logger_name, verbose_level:int=0, filename:str=None):
    level = None
    if verbose_level == -1:
        level = logging.CRITICAL
    if verbose_level is 0:
        level = logging.INFO
    elif verbose_level >= 1:
        level = logging.DEBUG

    formatter = logging.Formatter(fmt="%(asctime)-10s%(message)s", datefmt="%H:%M:%S")

    stdout_handler = ColorizingStreamHandler()
    stdout_handler.setFormatter(formatter)
    stdout_handler.stream = sys.stderr

    if not filename:
        filename = 'last.log'
    file_handler = logging.FileHandler(filename=filename, mode='w')
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(stdout_handler)
    root.addHandler(file_handler)

    root.setLevel(level)

    return logging.getLogger(__name__)


class Automaton:
    """
    An automaton has three types of states: `acc`, `dead`, normal.
    For a run to be accepted, it should satisfy:
      G(!dead) & GF(acc)
    Thus, in the automaton `dead` states has the property that they are `trap` states.
    If there are no `acc` states, acc is set to True.
    If there are no `dead` states, dead is set to False.
    """
    def __init__(self,
                 states,
                 init_state,
                 acc_states,
                 dead_states,
                 is_safety,  # `safety` means an automaton encodes rejecting finite traces
                 edges:'tuple of ((src,dst),set of labels) where label is a tuple of literals'):
        self.states = states
        self.init_state = init_state
        self.acc_states = acc_states
        self.dead_states = dead_states
        self.edges = edges
        self.propositions = self._get_propositions()
        self.is_safety = is_safety

        assert self.acc_states
        assert not (self.is_safety and len(self.dead_states) == 0), str(self)

    def _get_propositions(self):
        propositions = set()
        for ((src,dst), labels) in self.edges:
            for label in labels:
                for lit in label:
                    atom = lit.strip('~').strip('!')
                    propositions.add(atom)
        return tuple(propositions)   # fixing the order

    def __str__(self):
        return 'states: %s, init_state: %s, acc_states: %s, edges: %s' % \
            (self.states, self.init_state, self.acc_states, self.edges)


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


def gff_2_automaton(gff_xml:str):  # -> init, states, edges (dict (src,dst) |-> labels), acc
    # TODOopt: (boolean) simplify transitions labels
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

    return init_state, states, edges, acc_states
