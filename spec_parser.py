import re
from python_ext import find_all, readfile


ENV_AUTOMATON_SPEC = "ENV_AUTOMATON_SPEC"
SYS_AUTOMATON_SPEC = "SYS_AUTOMATON_SPEC"


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


# class ModuleSpecification:
#     def __init__(self, module_name,
#                  inputs, outputs, macros_signals,
#                  prop_specs):
#         self.outputs = tuple(outputs)
#         self.inputs = tuple(inputs)
#         self.macros_signals = tuple(macros_signals)
#         self.prop_specs = tuple(prop_specs)
#
#     @property
#     def signals(self):
#         return self.inputs + self.outputs


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
    if not l.strip():
        return False

    if l.strip() in [ENV_AUTOMATON_SPEC, SYS_AUTOMATON_SPEC, 'VAR', 'DEFINE']:
        return True

    if l.split()[0].strip() == 'MODULE':
        return True

    return False


def parse_smv_module(module_lines, base_dir) -> (SmvModule,list,list):
    lines_without_spec = []
    assumptions = []
    guarantees = []

    module_name = module_inputs = None
    now_parsing = False
    is_parsing_guarantees = None
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
                is_parsing_guarantees = l == SYS_AUTOMATON_SPEC

            elif 'MODULE' in l:
                # simple parser: assumes all inputs on the same line:
                match = re.fullmatch('MODULE *([\w_@\.]+) *(\([\w_@\. ,]*\))? *(--.*)*', l)
                assert match, 'uknown format\n' + l
                assert len(match.groups()) == 3, 'unknown format\n' + l
                module_name = match.groups()[0]
                inputs_token = match.groups()[1]
                module_inputs = re.findall('[\w_\.@]+', inputs_token or '')

            else:
                now_parsing = False
        else:
            if now_parsing:
                file_name = re.fullmatch('!? *([\w_\-\.]+\.gff).*', l).groups()[0]
                file_content = readfile(base_dir + '/' + file_name)
                data = PropertySpec(l,
                                    not l.startswith('!'),
                                    is_parsing_guarantees,
                                    file_content)
                (assumptions, guarantees)[is_parsing_guarantees].append(data)

        if not now_parsing:
            lines_without_spec.append(l_raw)

    module = SmvModule(module_name, module_inputs, '', '\n'.join(lines_without_spec), False, False)
    return module, assumptions, guarantees


def parse_smv(smv_lines:list, base_dir) -> dict:   # {module_name: Specification}
    lines_a_g_by_module_name = dict()
    module_start_indices = find_all(lambda l: l.startswith('MODULE'),
                                    smv_lines)
    for i,start in enumerate(module_start_indices):
        end = module_start_indices[i+1] \
            if i != len(module_start_indices) - 1 \
            else \
            len(smv_lines)

        module_without_spec, assumptions, guarantees = \
            parse_smv_module(smv_lines[start:end], base_dir)

        lines_a_g_by_module_name[module_without_spec.name] = (module_without_spec, assumptions, guarantees)

    return lines_a_g_by_module_name


# def parse_macros_signals(define_section:str) -> list:  # TODO: good to have: check that the signals used in
#                                                        # the automata are defined in the module
#    all_signals = list()
#    lines = define_section.splitlines()
#    for l in lines:
#        match = re.fullmatch('([a-zA-Z0-9_@]+) *: *=.*', l.strip())    # matching "ided_92 := ..."
#        if match:
#            signals = match.groups()
#            assert len(signals) == 1, str(signals) + ' :found on: ' + l
#            all_signals.append(signals[0])
#
#    return all_signals
