# SMV format for synthesis. A converter from it to the SYNT format.

Contains two conversion tools:

1. From our specification format (`SMV` file with goal automata files) to    
   SYNTCOMP with liveness guarantees format     
   (that we use for the synthesis with liveness tool): 

    - the main script file is `spec_2_aag.py`
    - `spec_2_aag.py` uses `spec_2_smv.py` that translates     
     our extended SMV format into the standard `SMV` format     
     that can be then later understood by aiger tools

2. From the SYNTCOMP with liveness guarantees format to the HWMCC format.


# Requirements

- `swig`   
  in the directory `aiger_swig` run `make_swig.sh`   
  (tested with version `2.0.11`, likely works with any `2.0.x`)

- aiger tools http://fmv.jku.at/aiger/    
  Tested with version `1.9.9`.      
  _Important_: change `aigor.c:135` line to `out = aiger_not(src->outputs[0].lit);`.    
  Should be in your PATH.

- `smvflatten` from http://fmv.jku.at/smvflatten/      
  Tested with version `1.2.5`.      
  Should be in your PATH.

- GOAL from http://goal.im.ntu.edu.tw/       
  Tested with version from `2014.11.17`.      
  Configure the path in `config.py`.


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

If you get import error -- run `setup.sh` from `aisy`.


# Authors
Ayrat Khalimov     
Email at gmail: ayrat.khalimov.
