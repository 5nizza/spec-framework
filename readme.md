# Specification to SYNT-AIGER converters

Contains two conversion tools:

1. From our specification format (`smv` file with goal automata files) to SYNT-AIGER-LIVE format (that we use for the synthesis with liveness tool): 
    - the main script file is `spec_2_aig.py`
    - that script file uses the script `spec_2_smv.py` which itself translates our specification smv format into `smv` format that can be then later understood by aiger tools

2. From SYNT-AIGER-LIVE format to HWMCC format (with justice).

Description of our specification format is at https://verify.iaik.tugraz.at/research/bin/view/Ausgewaehltekapitel/PARTI


# Requirements and Setup

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

- Modify `config.sh` and provide the path to `iimc` model checker.
  This is needed only if you plan to use `mc.sh` -- 
  it is a wrapper around a model checker for HWMCC format; used by `check_model.sh`,
  or you plan to use `check_model.sh` (a helper to verify models in the modified SYNTCOMP format).
  IIMC model checker can be downloaded at http://ecee.colorado.edu/wpmu/iimc/


# Warning
Not very user-friendly.


# Authors
Ayrat Khalimov and the SCOS group at TU Graz.
Email on gmail: ayrat.khalimov.
