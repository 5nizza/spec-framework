import re

from python_ext import find, find_all, readfile
from spec_2_smv import get_guarded_block, get_variables

ENV_AUTOMATON_SPEC = "ENV_AUTOMATON_SPEC"
SYS_AUTOMATON_SPEC = "ENV_AUTOMATON_SPEC"


class PropertySpec:
    @staticmethod
    def init_empty():
        return PropertySpec(None, None, None, None)

    def __init__(self,
                 desc,
                 is_positive:bool or None,
                 is_guarantee:bool or None,
                 data):
        self.desc = desc
        self.is_positive = is_positive
        self.is_guarantee = is_guarantee
        self.data = data

    def __str__(self):
        return "Spec(desc=%s, data=%s, %s, %s)" % \
               (self.desc,
                self.data,
                ['assumption', 'guarantee'][self.is_guarantee],
                ['bad trace', 'good trace'][self.is_positive])

    __repr__ = __str__

    @property
    def is_bad_trace(self):   # TODO: refactor: use is_guarantee
        return not self.is_positive

    @property
    def is_formula(self):
        return self.input_type == "qptl"

    @property
    def is_automaton(self):
        return self.input_type == "automaton"

    @property
    def to_be_assumption(self):    # TODO: refactor: use is_guarantee
        return not self.is_guarantee


class ModuleSpecification:
    def __init__(self, module_name,
                 inputs, outputs, macros_signals,
                 prop_specs):
        self.outputs = tuple(outputs)
        self.inputs = tuple(inputs)
        self.macros_signals = tuple(macros_signals)
        self.prop_specs = tuple(prop_specs)

    @property
    def signals(self):
        return self.inputs + self.outputs

def get_all_sections(lines, section_name):
    inside_section = False
    sections = list()
    cur_data = None
    for l in lines:
        if not l.strip():
            continue
        if is_section_declaration(l) and inside_section:
            sections.append(cur_data)
            inside_section = False
        if inside_section:
            cur_data.append(l)
        if l.strip() == section_name:
            inside_section = True
            cur_data = list()


def is_section_declaration(l):
    if l.strip() in [ENV_AUTOMATON_SPEC, SYS_AUTOMATON_SPEC, 'VAR', 'DEFINE']:
        return True

    if l.split()[0].strip() == 'MODULE':
        return True

    return False


def parse_smv_module(module_lines, module_name, base_dir) -> (list,list,list):
    lines_without_spec = []
    assumptions = []
    guarantees = []

    now_parsing = False
    cur_data_list = None
    for l_raw in module_lines:
        l = l_raw.strip()
        if not l:
            if not now_parsing:
                lines_without_spec.append(l_raw)
            continue

        if l.startswith('--'):
            if not now_parsing:
                lines_without_spec.append(l_raw)
            continue

        if is_section_declaration(l):
            if l in [ENV_AUTOMATON_SPEC, SYS_AUTOMATON_SPEC]:
                now_parsing = True
                cur_data_list = (assumptions, guarantees)[l == SYS_AUTOMATON_SPEC]
            else:
                now_parsing = False
        else:
            if now_parsing:
                file_content = readfile(base_dir + '/' + l.strip('!').strip())
                data = PropertySpec(l,
                                    l.startswith('!'),
                                    cur_data_list==guarantees,
                                    file_content)
                cur_data_list.append(data)

        if not now_parsing:
            lines_without_spec.append(l_raw)

    return lines_without_spec, assumptions, guarantees


def parse_smv(smv_lines:list, base_dir) -> dict:   # {module_name: Specification}
    lines_a_g_by_module_name = dict()
    module_start_indices = find_all(lambda l: l.startswith('MODULE'),
                                    smv_lines)
    for i,start in enumerate(module_start_indices):
        end = module_start_indices[i+1] \
            if i != len(module_start_indices) - 1 \
            else \
            len(smv_lines)

        module_name = re.fullmatch('MODULE *([a-zA-Z0-9_@]+) *(.*',
                                   smv_lines[start].strip()
                                   ).groups()[0]

        module_without_spec, assumptions, guarantees = \
            parse_smv_module(smv_lines[start:end],
                             module_name,
                             base_dir)

        lines_a_g_by_module_name[module_name] = (module_without_spec, assumptions, guarantees)

    return lines_a_g_by_module_name


def parse_macros_signals(define_section:str) -> list:
    all_signals = list()
    lines = define_section.splitlines()
    for l in lines:
        match = re.fullmatch(' *([a-zA-Z0-9_@]+) *: *=.*', l)    # matching "  ided_92 := ..."
        if match:
            signals = match.groups()
            assert len(signals) == 1, str(signals) + ' :found on: ' + l
            all_signals.append(signals[0])

    return all_signals