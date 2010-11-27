"""
Estimate the critical gains for sq2servo and sq1servo based on the
measured SA Ramp and SQ2 servo locking slopes.
"""


import auto_setup as aset
from pylab import *

from optparse import OptionParser

o = OptionParser(usage="""
               %prog [options] tuning_dir

where tuning_dir is the folder containg the tuning data.""")

def pretty(x, n=8, fmt='%8.4f'):
    out = ''
    for i in range((len(x)+n-1)/n):
        out += ' '.join([fmt % _x for _x in x[i*n:i*n+n]]) + '\n'
    return out

opts, args = o.parse_args()

for target in args:
    fs = aset.util.FileSet(target)
    sa = aset.SARamp.join([aset.SARamp(f) for f in fs.stage_all('sa_ramp')])
    sq2 = aset.SQ2Servo.join([aset.SQ2Servo(f) for f in fs.stage_all('sq2_servo')])

    print target
    sa.reduce(slope=1)
    s2s_gains = 1./sa.analysis['lock_slope']

    print 'SQ2 servo critical gain: '
    print pretty(s2s_gains)

    for s in [-1, +1]:
        sq2.reduce(slope=s)
        s1s_gains = 1./sq2.analysis['lock_slope'] / s2s_gains
        print 'SQ1 servo critical gain (sq2_slope=%i):' % s
        print pretty(s1s_gains)
        print
