"""
Estimate the critical gains for sq2servo and sq1servo based on the
measured SA Ramp and SQ2 servo locking slopes.
"""
from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div


import auto_setup as aset
import numpy as np

from optparse import OptionParser


def pretty(x, n=8, fmt='%8.4f'):
    out = ''
    for i in range(old_div((len(x)+n-1),n)):
        out += ' '.join([fmt % _x for _x in x[i*n:i*n+n]]) + '\n'
    return out


o = OptionParser(usage="""
               %prog [options] tuning_dir

where tuning_dir is the folder containg the tuning data.""")
o.add_option('-s','--stage',action='append')

opts, args = o.parse_args()

if opts.stage is None:
    opts.stage = ['sa_ramp', 'sq2_servo']

for target in args:
    fs = aset.util.FileSet(target)
    tuning = aset.util.tuningData(exp_file=fs.get('cfg_file'), data_dir='')

    if 'sa_ramp' in opts.stage:
        sa = aset.SARamp.join([aset.SARamp(f) for f in fs.stage_all('sa_ramp')])
        sa.tuning = tuning
        sa.reduce(slope=1)
        s2s_gains = old_div(1.,sa.analysis['lock_slope'])
        print('SQ2 servo critical gain: ')
        print(pretty(s2s_gains))

    if 'sq2_servo' in opts.stage:
        sq2 = aset.SQ2Servo.join([aset.SQ2Servo(f) \
                                      for f in fs.stage_all('sq2_servo')])
        sq2.tuning = tuning
        for s in [-1, +1]:
            sq2.reduce(slope=s)
            s1s_gains = 1./sq2.analysis['lock_slope'] / s2s_gains
            print('SQ1 servo critical gain (sq2_slope=%i):' % s)
            print(pretty(s1s_gains))
            print()

    if 'sq1_ramp' in opts.stage:
        sq = aset.SQ1Ramp.join([aset.SQ1Ramp(f)
                                for f in fs.stage_all('sq1_ramp')])
        sq.tuning = tuning
        sq.reduce()
        for direction in ['up', 'dn']:
            crit_gains = old_div(-4096.,sq.analysis['lock_%s_slope' % direction])
            crit_gains[np.isnan(crit_gains) + np.isinf(crit_gains)] = 0.
            # Reformat
            n_row, n_col = sq.data_shape[:2]
            crit_gains.shape = (n_row, n_col)
            print('Full chain critical gains by column:')
            for col, col_data in enumerate(crit_gains.transpose()):
                print('Column %i' % col)
                print(pretty(col_data, fmt='%8.2f'))
            print()

