#!/bin/bash

MY_DIR=`dirname $0`
GET_NOF_PROPERTIES=$MY_DIR/get_nof_properties.py

. ./config.sh

if [ "$#" -ne 1 ]
then
    echo "Argument is missing: Usage:"
    echo "mc <HWMCC_model_file>"
    exit -1
fi

MODEL=$1

# With IIMC we need to specify the index of a property  we want to check,
# by default it checks only the first one(?)
nof_properties=`$GET_NOF_PROPERTIES $MODEL`
echo " The number of properties to be checked is "$nof_properties"..."

mc_success=1
for pi in $(seq 0 `expr $nof_properties - 1`) 
do
    echo "  checking property #"$pi
    iimc_out=`$IIMC_CHECKER $MODEL --pi $pi`
    iimc_rc=$?
    if [[ $iimc_rc != 0 ]]
    then
      echo "  IIMC exited abnormally, interrupting model checking"
      exit -1
    fi
    
    # We need to check the last output line. 
    # If it is '0' -- the circuit is correct, if '1' - incorrect.
    iimc_answer=`echo "$iimc_out" | tail -n 1`    # quotations "" to preserve new lines

    if [[ $iimc_answer != 0 ]]
    then
        echo "  IIMC model checking: the resulting circuit is incorrect!!!!!!!!!!!"
        exit -1
    fi
    echo "  done with property #"$pi": correct"

done

echo " Model checking is done, the circuit is correct"

exit 0
