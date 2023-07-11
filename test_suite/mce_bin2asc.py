#!/usr/bin/python

from __future__ import print_function
from mce_data import MCEFile
import sys
from numpy import *

if len(sys.argv) <= 1:
    print('Give me raw file names.')
    sys.exit(1)

for f in sys.argv[1:]:
    d = MCEFile(f).Read().data[0]
    fout = open(f+'.txt', 'w')
    savetxt(fout, d, '%i', '\n')
