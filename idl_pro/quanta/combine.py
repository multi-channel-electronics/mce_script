"""
Creates an experiment.cfg template from files containing the
output from measure_quanta.pro
"""

import sys
from glob import glob
from numpy import *

if len(sys.argv) <= 1:
    print """
    Usage:   %s   <file_template> [ rescale ]
        file_template should be printf-style formatting string with a single %%i argument.
        rescale is an integer (default 1) that multiplies the flux quanta.
    """ % sys.argv[0]
    sys.exit(1)

if len(sys.argv) < 3:
    rescale = 1
else: 
    rescale = int(sys.argv[2])

if len(sys.argv) < 4:
    def_phi0 = 8192
else:
    def_phi0 = int(sys.argv[3])

nrow = 41
ncol = 32
quanta = zeros((nrow, ncol), dtype='int')
quanta[:,:] = def_phi0

for rc in [1,2,3,4]:
    f = glob(sys.argv[1] % rc)
    if len(f) ==0:
        print 'No file for RC%i' % rc
        continue
    lines = open(f[0]).readlines()
    for l in lines:
        w = l.split()
        if len(w) == 0:
            continue
        if w[0] == 'Good:':
            r, c, q = int(w[1]), int(w[2]), float(w[5])
            quanta[r,c+(rc-1)*8] = q

print 'flux_quanta_all = ['
for c in range(ncol):
    outstr = '/* %2i */ ' % c
    for r in range(nrow):
        outstr += '%5i' % int(quanta[r,c])
        if c != ncol-1 or r != nrow-1:
            outstr += ','
    print outstr
print '];'
