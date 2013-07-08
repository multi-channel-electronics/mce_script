import auto_setup as aset
from auto_setup.util import mas_path
import numpy as np
import os, sys

from optparse import OptionParser

o = OptionParser(usage="""
               %prog [options] tuning_dir stage

where tuning_dir is the folder containg the tuning data and stage is
one of sa_ramp, sq2_servo, sq1_ramp, or sq1_ramp_tes.""")
o.add_option('-m','--median',action='store_true',default=False,
             dest='do_median',help='replace zeros with column median')
o.add_option('--span',type=float,default=1.5,
             help='minimum number of phi0 one can expect to find in the data.')
opts, args = o.parse_args()
if len(args) != 2:
    o.error('Provide exactly two arguments.')

tuning_dir = args[0]
stage = args[1]

# Protect user
if not tuning_dir[0] == '/' and not os.path.exists(tuning_dir):
    print 'Cannot find "%s", looking in $MAS_DATA...' % tuning_dir
    tuning_dir = mas_path().data_dir() + tuning_dir

fs = aset.util.FileSet(tuning_dir)
files = fs.stage_all(stage)
if len(files) == 0:
    print 'No files found for stage %s' % stage
    sys.exit(1)

if stage == 'sa_ramp':
    ramps = [aset.series_array.SARamp(f) for f in files]
    out_format = 'column'
elif stage == 'sq2_servo':
    ramps = [aset.sq2_servo.SQ2Servo(f) for f in files]
    out_format = 'column'
elif stage == 'sq1_ramp' or stage == 'sq1_ramp_check':
    ramps = [aset.SQ1Ramp(f) for f in files]
    out_format = 'array'
elif stage == 'sq1_ramp_tes':
    ramps = [aset.SQ1RampTes(f) for f in files]
    out_format = 'array'
else:
    print 'Unsupported stage argument "%s".' % stage

sq = ramps[0].join(ramps)

periods = []
if stage == 'sa_ramp':
    if sq.bias_style == 'ramp':
        sq.reduce1()
        sq = sq.subselect()
    lead = 0
else:
    lead = 10  # skip the pre-servo

data = sq.data[:,lead:]

# Set the scan width so that there is at least another phi0 available
n = data.shape[1]
n_phi0 = int(n / opts.span)
width = n - n_phi0            #
width = max(width, n/8)       # at least n/8!
width = min(width, n_phi0*2)  # at most 2*phi0 

print 'Keeping %i of %i points' % (n, sq.data.shape[-1])
print 'Traveling segment of length %i' % width

p = aset.servo.period(sq.data, width=width)

periods = p * sq.d_fb

n_rc = len(periods)/8
stage_keys = {
    'sa_ramp': 'sa_flux_quanta',
    'sq2_servo': 'sq2_flux_quanta',
    'sq1_ramp': 'flux_quanta_all',
    'sq1_ramp_check': 'flux_quanta_all',
    'sq1_ramp_tes': 'tes_quanta',
    }

name = stage_keys[stage]
s = name + ' = [\n'
if out_format == 'column':
    for i in range(n_rc):
        s += '        '+','.join([' %5i' % int(x) for x in periods[i*8:i*8+8]])
        if i == n_rc - 1:
            s += ' ];'
        else:
            s += ',\n'
elif out_format == 'array':
    n_row, n_col = sq.data_shape[-3:-1]
    if periods.size != n_row*n_col:
        print 'I do not know how to reduce this multi-bias data...'
        sys.exit(1)
    periods.shape = (n_row, n_col)
    if opts.do_median:
        # replace zeros with the column median where available
        for c in range(0,n_col):
            _s = periods[:,c]!=0
            if _s.sum() > 0:
                periods[~_s,c] = int(round(np.median(periods[_s,c])))
    # Danger time
    pad = ','.join(['0' for x in range(41-n_row)])
    
    for i in range(n_col):
        s += ' /* c%02i */ ' % sq.cols[i] + \
             ','.join([' %5i' % int(x) for x in periods[:,i]])
        if pad != '':
            s += ',' + pad
        if i == n_col - 1:
            s += ' ];'
        else:
            s += ',\n'
        
print s
