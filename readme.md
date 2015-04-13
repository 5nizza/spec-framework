# Specification to SYNT-AIGER converters

Contains two conversion tools:

1. From our specification format (`smv` file with goal automata files) to SYNT-AIGER-LIVE format (that we use for the synthesis with liveness tool): 
    - the main script file is `spec_2_aig.py`
    - that script file uses the script `spec_2_smv.py` which itself translates our specification smv format into `smv` format that can be then later understood by aiger tools

2. From SYNT-AIGER-LIVE format to HWMCC format (with justice).

Description of our specification format is at https://verify.iaik.tugraz.at/research/bin/view/Ausgewaehltekapitel/PARTI


# Requirements

- aiger tools http://fmv.jku.at/aiger/
  tested with version `1.9.4`

- `smvflatten` from http://fmv.jku.at/smvflatten/
  tested with version `1.2.4`

- GOAL from http://goal.im.ntu.edu.tw/
  tested with version from `2014.11.17`


Put `smvflatten` and aiger tools into your path. Set up in `config.py` your path to `goal`.


# Warning
Not very user-friendly.


# Authors
Ayrat Khalimov and the SCOS group at TU Graz.
Email on gmail: ayratkhalimov.