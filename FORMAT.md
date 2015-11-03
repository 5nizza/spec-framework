Format
======

The extended SMV format provides a 'convenient way' to mix
implementations and 'holes to be synthesized'.

Specification Languages
-----------------------

`spec_2_smv` translates the following languages:

* LTL (`LTL_SPEC`) or PLTL (`PLTL_SPEC`)
* (modified) ω-Regex (`ORE_SPEC`)
- Buechi automata in [GOAL](http://goal.im.ntu.edu.tw) format (`AUTOMATON_SPEC`)


### LTL Syntax
The LTL and PLTL syntaxes directly correspond to the [format](http://buchi.im.ntu.edu.tw/index.php/help/qptl/) used in GOAL.
We do not support path quantifiers `A` and `E`.
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

Our ω-Regex format supports operators `*`, `+`, `|`, and `?`. 
Note that there is **no** negation operator, except

- for negating the whole expression, i.e., 
  expressions of the form `!(<reg expression without negations>)`, and
- negating atomic propositions.

For symbols, ω-Regex expressions use propositional alphabet (in terms of GOAL).
Thus, every symbol represents a proposition, which can be true or false.
E.g., to specify in your regular expression the proposition `p` is true, 
write `p`, and write `~p` or `!p` to specify that `p` is false.

Coherent words are interpreted as single propositions by GOAL. 
E.g., `input` is a valid variable name. 
Inputs, which are to appear in sequence, shall be separated by a space.

You can use `.` to specify `True` (aka "any values of propositions").
Multiple uses of the dot still need to be separated by spaces.

You can use `,` to specify that two propositions should hold in the same 
time step. 
For example, `(.* g1,g2){.}` means "eventually `g1` and `g2`
are true in the same time step", while `(.* g1 g2){.}` means "eventually 
`g1` is followed by `g2` in the next time step".

#### Some limitations

By default, GOAL uses a classical alphabet for ω-Regex, 
while we use the propositional alphabet. 
Thus, we implicitly transform `!p` and `~p` into `not_p`,
and `a,b` into `a_and_b`,
then call GOAL's translation algorithms,
which returns an automaton with classical alphabet,
and then we translate the automaton with classical alphabet into 
an automaton with propositional alphabet.

Because of these implicit transformations, the strings `_and_` and `not_` 
_are not allowed_ as parts of variable names.
Using them will cause an assertion error.

When using negation and `,` operators, 
there should be no whitespace between the operator and the variable name. 
I.e., 
for instance,
`a,~b` will yield `a_and_not_b`,
but `a , ~ b` will yield bogus. 
Our regex transformation tool will not complain about bogus, 
but GOAL will raise an error, when trying to convert these.

Specification Types
-------------------

`spec_2_smv` distinguishes environment assumptions and system guarantees. 
Assumptions are prefixed with `ENV`, while guarantees are prefixed with `SYS`. 
Thus, now, the following specification section headers are supported:

* `ENV_AUTOMATON_SPEC`, `SYS_AUTOMATON_SPEC`
* `ENV_LTL_SPEC`, `SYS_LTL_SPEC`
* `ENV_PLTL_SPEC`, `SYS_PLTL_SPEC`
* `ENV_ORE_SPEC`, `SYS_ORE_SPEC`


Examples
--------

### LTL examples

*A implies B (in the first time step)*  
`A -> B`

*Every request is granted*  
`G (req -> F grant)`


### ω-Regex examples

*initially: A and not B*  
`a,~b`

*GF True*  
`{.}`


### Short format examples

The directory `tests` contains more interesting examples.
Usually, the module with specification should be named `main`, but often the tool 
can recognize such module
(see also [Semantic Sugar](#sugar) and [Limitations](#limitations)).

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

_EXPERIMENTAL, CAN BE REMOVED_

A module with assumptions and guarantees, but not being called `main`, 
will be renamed to `main`, unless the main module already exists. 

A module may be given a name (also called `description`) by using annotations. 
The following comments can be used and are equivalent:

* `--#name <name>`
* `--#desc <name>`
* `-- #name <name>`
* `-- #desc <name>`
* `-- #name: <name>`
* `-- #desc: <name>`

As you can see, the hash symbol (`#`) inside a comment denotes an annotation. `<name>` stands for the name given to the module, which may consist of alphanumeric characters and underscores only. Multiple uses of the same annotation will result in the latter overwriting the previous.


<a id='limitations'/> Limitations
---------------------------------

* every property should take only one line, and a line can contain only one property
* a module named `main` must be given
* only one module (the `main` module) can have controllable variables 
  and properties.
  In such module, controllable variables may depend on __any__ other symbol
  of __any__ module.
