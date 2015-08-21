from os import remove
from tempfile import NamedTemporaryFile

from config import GOAL
from common import setup_logging
from python_ext import find, readfile, stripped
from shell import execute_shell
from structs import Automaton

import logging
logger = logging.getLogger(__name__)


def get_tmp_file_name(prefix='tmp_'):
    tmp = NamedTemporaryFile(prefix=prefix, delete=False)
    return tmp.name


def execute_goal_script(script: str) -> str:
    """
    :return: stdout as printed by GOAL
    """

    script_tmp_file_name = get_tmp_file_name("goal_script_")
    with open(script_tmp_file_name, 'w') as f:
        f.write(script)
        logger.debug(script)

    cmd_to_execute = '%s batch %s' % (GOAL, script_tmp_file_name)
    res, out, err = execute_shell(cmd_to_execute)
    assert res == 0 and err == '', 'Shell call failed:\n' + cmd_to_execute + '\nres=%i\n err=%s' % (res, err)

    remove(script_tmp_file_name)
    return out


def execute_translation(what: str, formula: str, options: str="") -> str:
    output_file_name = get_tmp_file_name("goal_trans_")
    template = "translate {what} {option} -o {output} \"{formula}\";"
    script = template.format(what=what, option=options, formula=formula,
                             output=output_file_name)
    execute_goal_script(script)
    result = readfile(output_file_name)
    remove(output_file_name)
    return result


def strip_unused_symbols(gff_automaton_text: str) -> str:
    # GOAL may produce automaton
    # whose alphabet contains symbols
    # not used in any transition labels
    # here we remove unused propositions from the alphabet

    lines = gff_automaton_text.splitlines()

    alphabet_start = find(lambda l: '<Alphabet' in l, lines)
    alphabet_end = find(lambda l: '</Alphabet' in l, lines)

    if alphabet_start == -1 or alphabet_end == -1:
        return gff_automaton_text

    trans_start = find(lambda l: '<TransitionSet' in l, lines)
    trans_end = find(lambda l: '</TransitionsSet' in l, lines)

    lbl_lines = list(filter(lambda l: '<Label' in l, lines[trans_start + 1:trans_end]))

    used_labels = set()
    for lbl_line in lbl_lines:
        # <Label>~g ~r</Label>
        #: :type: str
        lbls = lbl_line[lbl_line.find('>') + 1:
                        lbl_line.find('<', lbl_line.find('>'))]
        lbls = stripped(lbls.replace('~', '').split())
        used_labels.update(lbls)

    # now construct the result
    result = lines[:alphabet_start + 1]
    for lbl in filter(lambda l: l != 'True', used_labels):
        result.append("        <Proposition>%s</Proposition>" % lbl)

    result += lines[alphabet_end:]

    return '\n'.join(result)
