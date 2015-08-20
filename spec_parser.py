import re
from python_ext import find_all, readfile
from structs import SmvModule, PropertySpec, SpecType
from itertools import chain

# list of all possible system and environment specifications
SPECS = list(chain(*[("ENV_{}".format(spec), "SYS_{}".format(spec)) for spec in SpecType.__members__]))

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
    return l.strip() and l.split()[0].strip() in SPECS + ['VAR', 'DEFINE', 'MODULE']

    if not l.strip():
        return False

    if l.strip() in SPECS + ['VAR', 'DEFINE']:
        print(l)
        return True

    if l.split()[0].strip() == 'MODULE':
        print(l)
        return True

    return False

def get_spec_type_for_section(section_declaration:str) -> SpecType:
    assert section_declaration.endswith("_SPEC")
    assert section_declaration.startswith("SYS_") or section_declaration.startswith("ENV_")
    spec_name = section_declaration[4:] # magic
    return SpecType[spec_name]

def is_guarantee(section_declaration:str) -> bool:
    return section_declaration.startswith("SYS_")

def parse_smv_module(module_lines, base_dir) -> (SmvModule,list,list):
    lines_without_spec = []
    assumptions = []
    guarantees = []
    desc = None

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
            else:
                match = re.fullmatch("(--| )*#(name|desc) ([\w_]+).*", l)
                if(match):
                    desc = match.groups()[2]
            continue

        if is_section_declaration(l):
            if l.endswith("_SPEC"):
                now_parsing = True
                is_parsing_guarantees = is_guarantee(l)
                spec_type = get_spec_type_for_section(l)

            elif 'MODULE' in l:
                # simple parser: assumes all inputs on the same line:
                match = re.fullmatch('MODULE *([\w_@\.]+) *(\([\w_@\. ,]*\))? *(--.*)*', l)
                assert match, 'unknown format\n' + l
                assert len(match.groups()) == 3, 'unknown format\n' + l
                module_name = match.groups()[0]
                inputs_token = match.groups()[1]
                module_inputs = re.findall('[\w_\.@]+', inputs_token or '')

            else:
                now_parsing = False
        else:
            if now_parsing:
                if spec_type == SpecType.GFF_SPEC:
                    file_name = re.fullmatch('!? *([\w_\-\.]+\.gff).*', l).groups()[0]
                    data = PropertySpec(file_name,
                                        not l.startswith('!'),
                                        is_parsing_guarantees,
                                        base_dir + '/' + file_name,
                                        spec_type)

                elif spec_type == SpecType.OMEGA_REGEX_SPEC:
                    is_false = l.startswith("!(") and l.endswith(")")
                    data = PropertySpec(l, not is_false, is_parsing_guarantees,
                                        l if not is_false else l[2:-1], spec_type)
                elif spec_type in [SpecType.LTL_SPEC, SpecType.PLTL_SPEC]:
                    data = PropertySpec(l, True, is_parsing_guarantees, l, spec_type)

                else:
                    assert False, "SpecType " + str(spec_type) + " can not be handled."

                if desc:
                    data.desc = desc
                    desc = None

                (assumptions, guarantees)[is_parsing_guarantees].append(data)

        if not now_parsing:
            lines_without_spec.append(l_raw)

    module = SmvModule(module_name, module_inputs, '', '\n'.join(lines_without_spec), False, False)
    return module, assumptions, guarantees

def parse_smv(smv_lines:list, base_dir) -> {str: (SmvModule, list, list)}:   # {module_name: Specification}
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
