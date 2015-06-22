#!/bin/bash

MY_DIR=`dirname $0`

MC=$MY_DIR/mc.sh
SYNT_2_HWMCC=$MY_DIR/synt_2_hwmcc.py
FAIRNESS_2_JUSTICE=$MY_DIR/fairness_2_justice.py

if [ "$#" -ne 1 ]; then
    echo "Argument is missing: Usage:"
    echo "./check_model.sh <SYNT_model_file>"
    exit -1
fi

outfile_path=$1

outfile_hwmcc_path=`mktemp --suffix .aag`

echo "Translating the model into HWMCC format ... "
$SYNT_2_HWMCC $outfile_path | $FAIRNESS_2_JUSTICE > $outfile_hwmcc_path
rc=$?

if [[ $rc != 0 ]]
then
  echo "Conversion FAILED!!!"
  exit -1
fi

echo "Model checking ... "

$MC $outfile_hwmcc_path
rc=$?

if [[ $rc == 0 ]]
then
  echo "Model checking: OK"
  exit 0
else
  echo "Model checking: FAILED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  exit -1
fi