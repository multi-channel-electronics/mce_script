import auto_setup as aset
from pylab import *

from optparse import OptionParser

o = OptionParser(usage="""
               %prog [options] tuning_dir stage

where tuning_dir is the folder containg the tuning data and stage is
one of sa_ramp or sq2_servo.""")

opts, args = o.parse_args()
if len(args) != 2:
    o.error('Provide exactly two arguments.')

dir = args[0]
stage = args[1]

fs = aset.util.FileSet(dir)
files = fs.stage_all(stage)
if stage == 'sa_ramp':
    ramps = [aset.series_array.SARamp(f) for f in files]
elif stage == 'sq2_servo':
    ramps = [aset.sq2_servo.SQ2Servo(f) for f in files]
else:
    print 'Unsupported stage argument "%s".' % stage

periods = []
for sq in ramps:
    
    if stage == 'sa_ramp':
        if sq.data_style != 'rectangle':
            sq.reduce1()
            sq = sq.subselect()
        lead = 0
    else:
        lead = 10  # skip the pre-servo

    # Use only a bit near a zero crossing
    sq.data = sq.data[:,lead:]
    sgn = sign(sq.data - sq.data.mean(axis=1).reshape(-1,1))
    idx = array([(s != s[0]).nonzero()[0][0] for s in sgn])

    # Do not let idx exceed 1/4 of width
    n = sq.data.shape[1]
    idx = [ min(i, n/4) for i in idx ]
    wid = sq.data.shape[1] - max(idx)
    data = array([d[i:i+wid] for d,i in zip(sq.data, idx)]).astype('float')

    q = aset.servo.period_correlation(data, width=n/8)
    p = aset.servo.period(data, width=n/8)

    periods.extend(p * sq.d_fb)

n_rc = len(periods)/8
if stage == 'sa_ramp':
    s = 'sa_flux_quanta'
else:
    s = 'sq2_flux_quanta'
s += ' = [\n'
for i in range(n_rc):
    s += '        '+','.join([' %5i' % int(x) for x in periods[i*8:i*8+8]])
    if i == n_rc - 1:
        s += ' ];'
    else:
        s += ',\n'
print s
