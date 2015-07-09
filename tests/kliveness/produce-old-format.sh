#!/bin/bash

for f in `ls ../*.aag`; 
do 
  ~/projects/spec-framework/justice_2_safety.py $f $f.klive --k 10;
done;
