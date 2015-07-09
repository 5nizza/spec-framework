#!/bin/bash
for f in `find . -name "*.klive"`; 
do 
echo $f;
~/projects/aisy-classroom-akdv14/aisy.py -r $f; 
done;
