"""
Set up locked servo (looped-back) RC.  Manipulate the equilibrium
feedback by setting adc_offset.
"""
from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import range
from past.utils import old_div

from mce import mce
import numpy
from pylab import *
import time

class super_mce(mce):
    def __init__(self, *args, **kwargs):
        mce.__init__(self, *args, **kwargs)
        self.n_rc = len(self.read('rca', 'fw_rev'))
        # The col_map might need tweaking depending on what rcs are present.
        self.col_map = list(range(self.n_rc*8))

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

    init_servo = init_flux

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

class column(super_mce):
    """
    Simplified commands for controlling one column of an mce.
    """
    def __init__(self, rc, chan):
        super_mce.__init__(self)
        self.rc, self.chan = rc, chan
    
    ##
    def read_col(self, n=1, avg=False):
        # Reads column 0
        d = numpy.array(self.read_frames(n, data_only=True))[:,self.chan::self.n_rc*8]
        if avg:
            return d.mean(axis=0)
        return d

    def _colrow_param(self, param, vals=None, offset=None):
        c, p = 'rc%i'%(self.rc+1), param + '%i'%self.chan
        if vals is None:
            return self.read(c,p)
        vals = [int(x) for x in vals] # safetyize
        return self.write(c,p,vals)

    def _col_param(self, param, val=None):
        c = 'rc%i'%(self.rc+1)
        if val is None:
            return self.read(c,param)[self.chan]
        return self.write(c,param,[val],offset=self.chan)

    ##
    def adc_offset(self, vals=None):
        return self._colrow_param('adc_offset', vals)

    def flux_quanta(self, vals=None):
        return self._colrow_param('flx_quanta', vals)

    def gaini(self, val=None):
        return self._colrow_param('gaini', val)

    def fb_const(self, val=None):
        return self._col_param('fb_const', val)

    def sa_bias(self, val=None):
        return self._col_param('sa_bias', val)

    def sa_offset(self, val=None):
        return self._col_param('offset', val)


def permute(items):
    from random import random
    n = len(items)
    _items = [i for i in items]
    for i in range(n):
        j = int(random()*(n-i))
        _items[i], _items[n-1-j] = _items[n-1-j], _items[i]
    return _items

SAMPLE_NUM = 10
SAMPLE_DELAY = 90
ROWS = 33

INIT_ONLY=False
SOURCE_ROW = 4

if __name__ == '__main__':
    # Get MCE
    import sys
    if len(sys.argv) > 1:
        col = int(sys.argv[1])
    else:
        col = 0
    rc = 0 # ya, we're zero indexing.
    m = column(rc,col)

    # Essential setup
    m.reset()
    time.sleep(0.1)
    #m.write('cc', 'rcs_to_report_data', [1<<5])
    m.write('rca', 'sample_num', [SAMPLE_NUM])
    m.write('rca', 'sample_dly', [SAMPLE_DELAY])
    m.write('sys', 'row_len', [100])
    m.write('sys', 'num_rows', [ROWS])
    m.write('rca', 'num_rows_reported', [ROWS])
    m.write('cc', 'num_rows_reported', [ROWS])
    m.write('cc', 'data_rate', [10])
    m.write_columns('gaini', [0]*8)
    m.data_mode(0)
    m.servo_mode(1)
    
    # Other setup
    m.flux_quanta([7700]*ROWS)

    # Measure SQ1 FB response
    def col_avg():
        time.sleep(0.1) # let any recent settings set
        return old_div(mean(m.read_col()), SAMPLE_NUM)

    def check():
        z1 = old_div(m.read_col(), SAMPLE_NUM)
        time.sleep(0.5)
        z2 = old_div(m.read_col(), SAMPLE_NUM)
        return (abs(array(z1) - z2) > 100).astype('int')

    # Zero point
    m.sa_bias(0)
    m.sa_offset(0)
    m.fb_const(-8192)
    m.adc_offset([0]*ROWS)
    adc0 = col_avg()

    # Probe the ADC response to SQ1 fb
    m.fb_const(8191)
    adc1 = col_avg()
    m.fb_const(-8192)
    print('SQ1FB range coverage:  %8.2f to %8.2f =  %8.2f' % (adc0, adc1, adc1-adc0))
    dadc_dfb = old_div((adc1-adc0), (8191 + 8192))
    print('  dADC / dFB:          %8.4f' % (dadc_dfb))
    print('  Critical gain:       %8.2f' % (4096. / dadc_dfb / SAMPLE_NUM))
    # Probe ADC response to SA bias
    m.sa_bias(2000)
    adc1 = col_avg()
    m.sa_bias(0)
    print('SA range coverage:     %8.2f to %8.2f' % (adc0, adc1))
    dadc_dsa = old_div((adc1 - adc0), 2000) 
    print('  dADC / dSA:          %8.4f' % (dadc_dsa))
    
    # Probe ADC response to SA offset
    m.sa_offset(2000)
    adc1 = col_avg()
    m.sa_offset(0)
    print('SA offset coverage:     %8.2f to %8.2f' % (adc0, adc1))
    dadc_doff = old_div((adc1 - adc0), 2000)
    print('  dADC / dOffset:      %8.4f' % (dadc_doff))

    if INIT_ONLY:
        raise RuntimeError('stopping')

    # Set offset/bias to lock near FB=0
    adc = adc0 + dadc_dfb * 8192
    if adc > 0:
        m.sa_offset(-int(old_div(adc, dadc_doff)))
    else:
        m.sa_bias(-int(old_div(adc, dadc_dsa)))
    m.fb_const(0)
    
    # Those should work fine.  Pick a set of target feedbacks
    DAC_OK = 16000*.93 # don't flux jump immediately
    targets = old_div(-DAC_OK,2) + DAC_OK*arange(ROWS+1)/ROWS
    targets = array(permute(targets))
    targets[SOURCE_ROW] = -4000

    # Convert to adc_offsets
    adc_offset = targets * dadc_dfb
    m.adc_offset(adc_offset.astype('int'))

    # Set some dead pixels
    dead_rows = zeros(ROWS, 'bool')
    dead_rel = [-3,14,15,20]
    for d in dead_rel:
        dead_rows[(SOURCE_ROW + d + ROWS)%ROWS] = True
    
    # Lock it
    if 1:
        gains = -100 * ones(ROWS)
        gains[dead_rows] = 0
        m.gaini(gains)
        m.servo_mode(3)
        m.init_servo()
        m.data_mode(1)
        time.sleep(0.1)
        print('Lock points: ', old_div(m.read_col()[0],2**12))

    def trace(delay=0.01, steps=100, step_fn=None):
        t = 0
        data = []
        for i in range(steps):
            if step_fn is not None:
                step_fn(i)
            time.sleep(delay)
            data.append(m.read_col()[0])
        data = array(data)
        return data
        
    def curve(i):
        NW = old_div(STEPS,8)
        ao = ADC0 + DEPTH*exp(-(old_div(float((i-old_div(STEPS,2))),NW))**2)
        a = m.adc_offset()
        a[SOURCE_ROW] = ao
        m.adc_offset(a)
        
    # Run a curve
    print('Running a curve...')
    m.data_mode(1)
    m.flux_jumping(1)

    ADC0 = m.adc_offset()[SOURCE_ROW]
    DEPTH = (old_div(DAC_OK,2) - targets[SOURCE_ROW]) * dadc_dfb
    STEPS = 200
    data = trace(delay=0.01, steps=STEPS, step_fn=curve)
    fj = None

    # Unravel for data mode:
    data_mode = m.data_mode()
    if data_mode == 1:
        data = old_div(data, 2**12)
    elif data_mode == 2:
        data = old_div(data, 1218.)
    elif data_mode == 10:
        data = data / 1218 / 16
        fj = (2**16 + data) % 128

    print('Reached grand extreme of ', data[:,0].max())

    #
    idx = arange(ROWS-1)
    idx = idx + (idx >= SOURCE_ROW).astype('int') # rows that aren't the source
    ddata = (data - data[:10,:].mean(axis=0))[:,idx]

    print('Source row:   ', SOURCE_ROW)
    print('Top 10 departures:')
    deps = abs(ddata).max(axis=0)
    deps = sorted(zip(deps, idx))
    for dep, i in deps[-1:-11:-1]:
        print('  row %2i   %5f' % (i,dep))
    print()

    subplot(211)
    plot(data[:,idx])
    plot(data[:,SOURCE_ROW])
    title('Feedback; all rows')
    ylabel('FB (DAC units)')

    subplot(212)
    plot(ddata)
    title('Feedback; non-source rows')
    xlabel('Time step')
    ylabel('FB - FB[t=0] (DAC units)')

    savefig('xtalk.png')
    show()
