import mce
import sys
from optparse import OptionParser
from numpy import *

MCE_COLS = 8

o = OptionParser()
o.add_option('-n','--n-frames',type='int',default=1,
             help='number of frames to average when determining feedback')
o.add_option('-r','--row',type='int',default=0,
             help='the row to use for all columns')
o.add_option('--rows',type='string',default='',
             help='use this to specify different rows for each columns, e.g.\n' \
                 '--rows "0 1 2 1 2 1 2 0"')
o.add_option('--rc',type='string',default='a',
             help='specify readout card (1,2,3,4 or a for all). Default is "a".')
o.add_option('--restore',action='store_true',default=False,
             help='restart the MCE servo (servo_mode=3 + flx_lp_init)')
opts, args = o.parse_args()

m = mce.mce()


# Determine name and number of readout cards
rc = 'rc%s'%opts.rc     # i.e. rc1, rc2, rc3, rc4, rca.
n_rc = len(m.read(rc, 'data_mode'))
n_cols = n_rc * MCE_COLS
n_rows = m.read('cc', 'num_rows_reported', array=False)

# This offset is applied to wide registers, like 'sq1 servo_mode'
if opts.rc == 'a':
    rc_ofs = 0
else:
    rc_ofs = (int(opts.rc)-1)*8

if opts.restore:
    print 'Restarting servo'
    m.write('sq1', 'servo_mode', [3]*n_cols, offset=rc_ofs)
    m.write(rc, 'flx_lp_init', [1])
    sys.exit()

lock_rows = [0]*n_cols

if opts.rows != '':
    lock_rows = [int(r) for r in opts.rows.split()]
else:
    lock_rows = [opts.row for r in range(n_cols)]


# Take the data in mode 1
m.write(rc, 'data_mode', [1])
frames = m.read_frames(opts.n_frames, data_only=True)
n_cols_read = len(frames[0]) / n_rows

# In the future, mce will work directly with numpy arrays...
frames = array(frames).reshape((-1,n_rows,n_cols_read))

# Set the fb_const values and turn off the servo
fb = mean(frames, axis=0) / 2**12
fb_const = [int(fb[lock_rows[i],i+rc_ofs]) for i in range(n_cols)]
print 'Setting fb_const = ', fb_const
m.write('sq1', 'fb_const', fb_const, offset=rc_ofs)
m.write('sq1', 'servo_mode', [0]*n_cols, offset=rc_ofs)
