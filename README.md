# SMV format for synthesis. A converter into the SYNTCOMP format.

Extended SMV format for synthesis is SMV + 

- comments to specify signals to be synthesized
- ability to write specifications in PLTL, omega-RE, and pure automata.

Read format description in [format.md](format.md).

These repository contains two conversion tools:

1. From extended SMV format 
   to
   SYNTCOMP GR1:

    - the main script file is `spec_2_aag.py`
    - `spec_2_aag.py` uses `spec_2_smv.py` that translates     
     the extended SMV format into the standard `SMV` format     
     that can be then later understood by AIGER tools

2. From models in the SYNTCOMP GR1 format into model checking tasks in the HWMCC format.


# Requirements

- `swig`   
  in the directory `aiger_swig` run `make_swig.sh`   
  (tested with version `2.0.11`, likely works with any `2.0.x`)

- aiger tools http://fmv.jku.at/aiger/    
  Tested with version `1.9.9`.      
  _Important_: change `aigor.c:135` line to `out = aiger_not(src->outputs[0].lit);`.    
  Should be in your `PATH`.

- `smvflatten` from http://fmv.jku.at/smvflatten/      
  Tested with version `1.2.5`.      
  Should be in your `PATH`.

- [GOAL](http://goal.im.ntu.edu.tw)      
  Tested with version from `2014.11.17`.      


# Configure

Run:

`./configure.py`

It creates local configuration files `config.py` and `config.sh`. 
You will be asked to edit those files.


# Run
Run: 

`./spec_2_aag.py <smv_spec_file>`


# Examples
Examples are in folder `tests`.


# Tests

`./run_tests.py`

or 

`./run_tests.py --aisy`

In the second version, the generated AIGER files will be given to `aisy` for synthesizing. 

NOTE: if you get import error -- run `setup.sh` from `aisy`.


# Authors
Ayrat Khalimov, Leo Prikler extended it to support omega-Reg, PLTL, and GR1 specifications.

Gmail me: ayrat.khalimov.


# Citing
Originally appeared in paper "Specification Format for Reactive Synthesis Problems" 
at [SYNT'15](http://formal.epfl.ch/synt/2015/).

