#!/bin/bash

# build aiger.so
gcc -c -fpic ./aiger.c && gcc -shared -o aiger.so aiger.o


#build swig wrappers
interface_file=aiger.i

swig -Wall -python -py3 $interface_file && 
gcc -O2 -fPIC -c aiger.c && 
gcc -O2 -fPIC -c aiger_wrap.c -I/usr/include/python3.4/ && 
gcc -shared aiger.o aiger_wrap.o -o _aiger_wrap.so 
