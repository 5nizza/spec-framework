There is a problem here:
suppose we have

MODULE module_with_spec
  some_spec

and we instantiate two instances of `module_with_spec`:

MODULE main
  inst1: module_with_spec();
  inst2: module_with_spec();

Then the final module should ensure that the spec is satisfied in _both_ instances.
To ensure this, we need to keep track of _all_ instances of `module_with_spec`, 
then in the `main` module we add their specs into the specification.

------------------------------

I currently use a hack for expressing justice properties:
- define them in SMV with `FAIRNESS`
- then literally replace `FAIRNESS` with `JUSTICE` in the output circuit

Better options?
- introduce specially named state variables like `justice_var`
- translate into AIGER without `JUSTICE` and then post-process: 
  add justice by referring to the special variable
- in this way we refer to the value of a latch, 
  hence, it is of the Moore type

Why is it better? 
- more control of what `smvtoaig` produces
- we can have more than a single justice property
- we can mix with fairness assumptions

Other options?
use `ltl2smv`: 
specify them using `LTLSPEC` and then use `my_ltl2smv` to produce a decent output
- we can use `LTLSPEC` directly




NOW:
- change to format: 
  - allow using several modules with to-be-synthesized-signals
  - use shorter notation `--controllable`
  - by default translate all signals from `DEFINE` to spec modules (and remove `common`)
  - add `SYS_AUTOMATON_SPEC`, `ENV_AUTOMATON_SPEC`
  - allow positive and negative automata for both assumptions and guarantees
    - allow positive safety automata


Introduce sections:
`LTLSPEC`, `AUTOMATON_SPEC`, `RE_SPEC`...
But we also need to specify assumptions -- so add sections:
`ENV_LTLSPEC`, `ENV_AUTOMATON_SPEC`, `ENV_RE_SPEC`...
... and handle all these sections.

All these sections can be placed in any module.
