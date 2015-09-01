from enum import Enum


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
                 edges: 'tuple of ((src,dst),set of labels) where label is a tuple of literals'):
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
        for ((src, dst), labels) in self.edges:
            for label in labels:
                for lit in label:
                    atom = lit.strip('~').strip('!')
                    propositions.add(atom)
        return tuple(propositions)   # fixing the order

    def __str__(self):
        return 'states: %s, init_state: %s, acc_states: %s, dead_states: %s, edges: %s' % \
            (self.states, self.init_state, self.acc_states, self.dead_states, self.edges)


class SmvModule:
    def __init__(self, name, module_inputs, desc, module_str, has_bad, has_fair):
        self.module_inputs = tuple(module_inputs)
        self.name = name
        self.desc = desc
        self.module_str = module_str
        self.has_bad = has_bad
        self.has_fair = has_fair

    def __str__(self):
        return 'module: %s (%s), def:\n%s' % (self.name, self.desc, self.module_str)


class SpecType(Enum):
    GFF_SPEC = 1
    LTL_SPEC = 2
    PLTL_SPEC = 3
    OMEGA_REGEX_SPEC = 4
    # Aliases
    AUTOMATON_SPEC = GFF_SPEC    # for legacy reasons
    LTLSPEC = LTL_SPEC           # since smvtoaig does it like this
    ORE_SPEC = OMEGA_REGEX_SPEC  # for lazy people


class PropertySpec:
    def __init__(self,
                 desc,
                 is_positive: bool or None,
                 is_guarantee: bool or None,
                 data,
                 type: SpecType):
        self.desc = desc
        self.is_positive = is_positive
        self.is_guarantee = is_guarantee
        self.data = data
        self.type = type

    def __str__(self):
        return "Spec(desc=%s, data=%s, %s, %s)" % \
               (self.desc,
                self.data,
                ['assumption', 'guarantee'][self.is_guarantee],
                ['bad trace', 'good trace'][self.is_positive])

    __repr__ = __str__
