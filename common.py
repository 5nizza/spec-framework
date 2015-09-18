import sys
import logging

from sympy import true, sympify
from sympy.core.symbol import Symbol
from sympy.logic.boolalg import simplify_logic, false

from ansistrm import ColorizingStreamHandler


def setup_logging(logger_name, verbose_level: int=0, filename: str=None):
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

    return logging.getLogger(logger_name)


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
