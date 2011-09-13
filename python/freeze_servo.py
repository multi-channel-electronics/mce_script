from numpy import *
from mce_control import *
import time

def check_lock():
    dm = mce.data_mode()
    mce.data_mode(0)
    nf = 30
    data = mce.read_data(nf)[:,ROW,:].astype('float')
    err, derr = data.mean(axis=0), data.std(axis=0)
    mce.data_mode(dm)
    return abs(err) < derr*2, err, derr

ROW = 0

mce = mce_control()

print check_lock()[0]

if 0:
    # Zong all squids except row 0.
    sq1_bias = mce.read('ac', 'on_bias')
    mce.write('ac', 'on_bias', sq1_bias[:1] + ([0]*40))
    mce.write('ac', 'off_bias', sq1_bias[:1] + ([0]*40))
    time.sleep(.1) # update...
    #mce.write('ac', 'row_order', [0]*41)
    time.sleep(.1)
    mce.write('ac', 'enbl_mux', [0])

# Check lock
#print check_lock()[0]

# Measure feedback
mce.data_mode(1)
data_gain = 2**12
NF = 10
data = mce.read_data(NF)[:,ROW,:].astype('float') / data_gain
fb, dfb = data.mean(axis=0), data.std(axis=0)

# Set this as the feedback.
print mce.io_rc_array_1d('fb_const')
mce.io_rc_array_1d('fb_const', fb.astype('int'))
print mce.io_rc_array_1d('fb_const')
mce.servo_mode(0)

# Check "lock"
print check_lock()[0]
