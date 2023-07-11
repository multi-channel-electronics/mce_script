"""
Set up feedback servo ramp on (disconnected) RC.  It's best to jumper the
amp inputs so that there is no drift in the error voltage level.
"""
from __future__ import division
from __future__ import print_function
from past.utils import old_div

from mce import mce
import numpy
from pylab import *
import time

class super_mce(mce):
    def __init__(self, *args, **kwargs):
        mce.__init__(self, *args, **kwargs)
        self.n_rc = len(self.read('rca', 'fw_rev'))

    def read_row(self, n=1, avg=False):
        d = numpy.array(self.read_frames(n, data_only=True))[:,:self.n_rc*8]
        if avg:
            return d.mean(axis=0)
        return d

    def write_columns(self, param, data):
        # Duplicate values across all rows in each column parameter
        for c, d in enumerate(data):
            rc, chan = old_div(c,8) + 1, c%8
            self.write('rc%i'%rc, param+'%i' % chan, [int(d)]*41)

    def servo_mode(self, mode=None):
        if mode is None:
            return self.read('rca', 'servo_mode')[0]
        else:
            self.write('rca', 'servo_mode', [mode]*8)
    
    def data_mode(self, mode=None):
        if mode is None:
            return self.read('rca', 'data_mode')[0]
        else:
            self.write('rca', 'data_mode', [mode])

    def init_flux(self):
        self.write('rca', 'flx_lp_init', [1])

    def flux_quanta(self, n):
        self.write_columns('flx_quanta', [n]*(self.n_rc*8))

    def flux_jumping(self, mode=None):
        if mode is None:
            return self.read('rca', 'en_fb_jump')[0]
        self.write('rca', 'en_fb_jump', [mode])

    def dt(self):
        nr, dr, rl = [self.read('cc', k)[0] for k in 
                      ['num_rows', 'data_rate', 'row_len']]
        return old_div(float(nr * dr * rl), 5e7)

if __name__ == '__main__':
    # Get MCE
    m = super_mce()
    # Set up error acq mode
    m.reset()
    time.sleep(0.1)
    m.data_mode(0)
    m.write('rca', 'sample_num', [10])
    m.servo_mode(1)
    m.write_columns('adc_offset', [0]*(m.n_rc*8))

    # Sample
    d1 = m.read_row(100, True)
    print('0-sample:')
    print(d1)
    # ADC_offset
    adc0 = old_div(d1, 10)
    m.write_columns('adc_offset', adc0)
    # Re-sample
    d2 = m.read_row(100, True)
    print('Check lock:')
    print(d2)

    # Set gains to servo at ~ 1000 FB / second
    target = -16300
    f_frame = 50e6 / 41 / 64
    e_gain = int(target * 4096 / f_frame)

    # RC2
    m.write_columns('gaini', ([0]*8)+([1]*8))
    # RC1
#    m.write_columns('gaini', ([1]*8)+([0]*8))
    m.write_columns('adc_offset', adc0 - old_div(e_gain,10))
    m.data_mode(1)
    m.servo_mode(3)

    m.init_flux()
    d3 = old_div(m.read_row(100), 4096)
    chan = d3[:,8]
    print(chan)
    plot(chan)
    show()
    
