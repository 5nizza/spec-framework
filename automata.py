from re import search, sub
from os import remove
from xml.etree import ElementTree
import logging

from common import reduces_to_true
from goal_utils import get_tmp_file_name, execute_goal_script, execute_translation, strip_unused_symbols
from python_ext import readfile
from siregex import to_regex, regex_to_proposition
from structs import Automaton, SpecType, PropertySpec

logger = logging.getLogger(__name__)


def automaton_from_gff(gff: str, complement: bool=False) -> Automaton:
    gff = strip_unused_symbols(gff)

    input_file_name = get_tmp_file_name()
    output_file_name = get_tmp_file_name()
    output_file_name2 = get_tmp_file_name()

    with open(input_file_name, 'w') as f:
        f.write(gff)

    complement_stmnt = '' if not complement else '\n$res = complement $res;'
    goal_script = """
$res = load "{input_file_name}"; {complement_stmnt}
$res = simplify -m fair -dse -ds -rse -rs -ru -rd $res;
$res = determinization -m bk09 $res;
acc -min $res;
save $res {output_file_name};
acc -max $res;
save $res {output_file_name2};
""".format(complement_stmnt=complement_stmnt,
           input_file_name=input_file_name,
           output_file_name=output_file_name,
           output_file_name2=output_file_name2)

    execute_goal_script(goal_script)

    gff = readfile(output_file_name)
    gff2 = readfile(output_file_name2)

    init_state2, states2, edges2, acc_states2 = gff_2_automaton_params(gff2)
    nacc_trap_states2 = get_nacc_trap_states(states2, acc_states2, edges2)
    if set(nacc_trap_states2).union(acc_states2) == set(states2):
        # safety automaton
        automaton = Automaton(states2, init_state2, acc_states2, nacc_trap_states2, True, tuple(edges2.items()))
    else:
        # contains both dead states, and accepting states
        init_state, states, edges, acc_states = gff_2_automaton_params(gff)
        nacc_trap_states = get_nacc_trap_states(states, acc_states, edges)
        automaton = Automaton(states, init_state, acc_states, nacc_trap_states, False, tuple(edges.items()))

    logger.info('after all manipulations: %s', ['liveness', 'safety'][automaton.is_safety])

    remove(input_file_name)
    remove(output_file_name)
    remove(output_file_name2)

    return automaton


def automaton_from_spec(spec: PropertySpec) -> Automaton:
    """
    We return an automaton that is 'positive deterministic Buchi'
    (we complement negated ones)
    (as an optimization the automaton has `fair` and `bad` states).
    As the last step we do `determinize`, which completes the automaton.
    The states are of three types:
      - acc non-trap      (aka `accepting states`)
      - acc trap          (aka `accepting states`)
      - non-acc non-trap  (aka `normal`)
      - non-acc trap      (aka `dead`)

    NOTE we should never fall-out of the automaton.
    """

    logger.info('building automaton from spec "%s" of type %s', spec.desc, spec.type)
    logger.debug(spec)
    # TODO better spec parsing
    get_gff = {SpecType.AUTOMATON_SPEC: readfile,
               SpecType.LTL_SPEC: ltl_2_automaton_gff,
               SpecType.PLTL_SPEC: pltl_2_automaton_gff,
               SpecType.ORE_SPEC: ore_2_automaton_gff}

    gff = get_gff[spec.type](spec.data)

    return automaton_from_gff(gff, not spec.is_positive)


def get_nacc_trap_states(states, acc_states, edges):
    nacc_states = set(states).difference(acc_states)
    nacc_trap_states = set()

    for s in nacc_states:
        s_edges = edges.get((s, s))
        if s_edges:
            if reduces_to_true(s_edges):
                nacc_trap_states.add(s)  # TODOopt: also replace edges with one trivial

    return nacc_trap_states


def gff_2_automaton_params(gff_xml: str):  # -> init, states, edges (dict (src,dst) |-> labels), acc
    # TODOopt: (boolean) simplify transitions labels
    # """
    # >>> print(gff_2_automaton(readfile('/tmp/tmp.gff')))
    # """
    states = set()
    edges = dict()  # (src,dst) -> set of labels
    root = ElementTree.fromstring(gff_xml)

    for transition_element in root.iter('Transition'):
        src = transition_element.find('From').text
        dst = transition_element.find('To').text
        lbl = transition_element.find('Label').text

        states.add(src)
        states.add(dst)

        if (src, dst) not in edges:
            edges[(src, dst)] = set()

        edges[(src, dst)].add(tuple(lbl.split()))

    init_state = root.find('InitialStateSet').find('StateID').text
    acc_states = set(elem.text for elem in root.find('Acc').iter('StateID'))

    return init_state, states, edges, acc_states


def ltl_2_automaton_gff(ltl: str) -> str:
    return execute_translation("QPTL", ltl, "-m ltl2ba -t nbw")


def pltl_2_automaton_gff(ltl: str) -> str:
    return execute_translation("QPTL", ltl, "-m pltl2ba -t nbw")


def check_correct_ore(omega_regex: str):
    match = search("[\W]not_", omega_regex)
    assert not match, "\"%s\" contains illegal sequence 'not_'" % omega_regex
    match = search("_and_", omega_regex)
    assert not match, "\"%s\" contains illegal sequence '_and_'" % omega_regex


def ore_2_automaton_gff(omega_regex: str) -> str:
    check_correct_ore(omega_regex)
    w_regex = to_regex(omega_regex)
    w_regex = sub("([\W])(?:[Tt]rue|\.)([\W])", "\\1True\\2", w_regex)

    result = execute_translation("ORE", w_regex, "-se -sa")
    result = sub("<Alphabet type=\"Classical\">",
                 "<Alphabet type=\"Propositional\">",
                 result)
    result = regex_to_proposition(result)

    return result
