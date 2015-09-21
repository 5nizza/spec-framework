Format
======
We extend the standard SMV format to allow specifications given not only as automatons but also using (past) linear temporal logic and ω-regular expressions.

Specification Languages
-----------------------
`spec_2_smv` translates the following languages:

* LTL (`LTL_SPEC`)
* PLTL (`PLTL_SPEC`)
* (modified) ω-Regex (`OMEGA_REGEX_SPEC` or `ORE_SPEC`)

In addition to the above, we also allow automatons given in the GOAL File Format (GFF), which are called `GFF_SPEC` or `AUTOMATON_SPEC` internally{ak: why `or`? can we only one?}. The filenames to these automatons shall be given one per line. Specifications given in one of the other formats are translated into automatons by the framework.

### LTL Syntax
The LTL syntax directly corresponds to the format used in GOAL, which is taken from [the Büchi Store](http://buchi.im.ntu.edu.tw/index.php/help/qptl/). In our current format we only support LTL and PLTL, so quantifiers (`A` and `E`) are not used.  
An incomplete list of LTL operators is:

    ------------------
    |  G   | Global  |
    |  F   | Final   |
    |  X   | Next    |
    |  U   | Until   |
    |  !   | Not     |
    |  &   | And     |
    |  |   | Or      |
    |  ->  | Implies |
    | <--> | Equals  |
    ------------------

Additional operators supported in PLTL include:

    -----------------
    | Y | Yesterday |
    | S | Since     |
    | O | Once      |
    -----------------

### ω-Regex Syntax
The ω-Regex Parser used has some restrictions, mainly that only the operators `*`, `+`, `|`, and `?` are allowed. This means, that there is **no** negation operator. As a special exception, we support negating the whole expression, i.e., expressions of the form `!(<reg expression without negations>)`, and negating propositions.

For symbols, ω-Regex expressions use propositional alphabet (in terms of GOAL).
This means, that every symbol represents a proposition, which can be true or false.
E.g., to specify in your regular expression the proposition `p` is true, 
write `p`, and write `~p` or `!p` to specify that `p` is false.

Coherent words are interpreted as single propositions by GOAL. This means, for instance, that `input` is a valid variable name. Inputs, which are to appear in sequence, shall be separated by a space.

You can use `.` to specify `True` (aka "any values of propositions").
Multiple uses of the dot still need to be separated by spaces, however.

You can use `,` to specify that two propositions should hold in the same 
time step. For example, `(.* g1,g2){.}` means that eventually `g1` and `g2`
are true in the same time step, while `(.* g1 g2){.}` means eventually 
`g1` is followed by `g2` in the next time step.

#### Some limitations

By default, GOAL uses a classical alphabet for ω-Regex, 
while the alphabet in `spec-framework` is propositional. In order to circumvent this,
we implicitly transform `!p` and `~p` into `not_p`,
and `a,b` into `a_and_b`,
then call GOAL's translation algorithms, 
and then translate the automaton with classical alphabet into an automaton 
with propositional alphabet.

Because of these implicit transformations, the strings `_and_` and `not_` 
are not allowed as parts of variable names and trying to use them will result
in an assertion error.

When using these operators, there should be no whitespace between the operator
and the variable name. While `a,~b` will for instance yield `a_and_not_b`,
`a , ~ b` will yield bogus. Our regex transformation tool will not complain about
bogus, but GOAL will raise an error, when trying to convert these.

Specification Types
-------------------

`spec_2_smv` allows environment assumptions as well as system guarantees. Assumptions have to be prefixed with `ENV`, while guarantees are prefixed with `SYS`. Using these prefixes for the aforementioned language types, the following section headers are currently supported:

* `SYS_AUTOMATON_SPEC` / `SYS_GFF_SPEC`
* `ENV_AUTOMATON_SPEC` / `ENV_GFF_SPEC`
* `SYS_LTL_SPEC`
* `ENV_LTL_SPEC`
* `SYS_PLTL_SPEC`
* `ENV_PLTL_SPEC`
* `SYS_OMEGA_REGEX_SPEC` / `SYS_ORE_SPEC`
* `ENV_OMEGA_REGEX_SPEC` / `ENV_ORE_SPEC`

The headers, which are listed on the same line seperated by `/` are aliases to each other and mean the same. Some of them are kept for legacy support, while others are for speeding up the writing of these specifications.

Examples
--------

### LTL examples
*A implies B (in the first time step)*  
`A -> B`

*A **always** implies b*  
G(A -> B)

*If a, then at some point b*  
`a -> F b`

### ω-Regex examples
*A and not B*  
`a,~b`

*GF True*  
`{.}`

### Short format examples
If you want more than toy examples, then looking at the `tests` directory would be a wise idea. Note, that even though we use meaningful names in our examples, you should use `main` for the module with the controllable input, unless you can be sure, that it will be recognized as the main module by our tool and thus be renamed as specified in [Semantic Sugar](#sugar). See [Limitations](#limitations) for the reason why.

    MODULE arbiter
      VAR
        r: boolean;
      VAR --controllable
        g: boolean; 

      SYS_LTL_SPEC
         -- all requests are granted
         G(r -> F g)
         -- no spurious grant in initial state
         r -> g

      SYS_ORE_SPEC
        -- no spurious grant after initial state
        !((r .* g+)* !r,!g+ !r,g {.})


    MODULE alarm_clock
      VAR
        set: boolean;
        snooze: boolean;

      VAR --controllable
        beep: boolean;

      SYS_LTL_SPEC
        G(set -> X (beep W snooze))
        G(snooze -> !beep)

      ENV_LTL_SPEC
        G(snooze -> F !snooze)


<a id='sugar'/> Semantic Sugar
------------------------------

In addition to the above, we provide some features to prettify the output of our tool or to "correct" user input, which would be found incorrect by one of the tools otherwise, but may be a desired form of input for the user himself.

A module, which has assumptions and guarantees, but is not called `main`, will be renamed to `main`, if no other module by that name exists, for compatibility with the tools for SMV modifications (most notably `smvflatten`, see [Limitations](#limitations)). This also makes that module the main module, whether this was intended by the user or not.

A module may be given a name (also called `description`) by using annotations. The following comments can be used and are equivalent:

* `--#name <name>`
* `--#desc <name>`
* `-- #name <name>`
* `-- #desc <name>`
* `-- #name: <name>`
* `-- #desc: <name>`

{ak: what is "giving a name to module" good for?}
{ak: do we need so many options?}
{ak: if we use # here -- should we use # for `--controllable`, too?}


As you can see, the hash symbol (`#`) inside a comment denotes an annotation. `<name>` stands for the name given to the module, which may consist of alphanumeric characters and underscores only. Characters after the first . Multiple uses of the same annotation will result in the latter overwriting the previous.


<a id='limitations'/> Limitations
---------------------------------

* every property should be one line only
* only one property can be given per line
* one module named `main` must be given (`spec_2_aag` only, because of `smvflatten`)
* only one module (the `main` module) can have controllable variables. 
  This is because current synthesis tools from SYNTCOMP 
  do not handle synthesis with partial information
  (i.e., scoped controllable variables).
  Thus, every controllable signal can depend on *any* other symbol of *any* module.
* also, only one module (again the `main` module) can have assumptions and guarantees,
  since they directly rely on controllable input. If more than one module 
  is to be given, then the module should be in plain SMV 
  (with neither properties nor controllable signals).
