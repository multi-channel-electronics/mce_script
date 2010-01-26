#!/usr/bin/python

import sys
from mce import *
from mce_data import *

from numpy import *
#from pylab import *

class sq2fbFile:
    def __init__(self, filename, new=False, n_rows=33):
        self.filename = filename
        if not new:
            self.load(n_rows)
        if new:
            open(self.filename, 'w').truncate(0)

    def load(self, n_rows):
        f = open(self.filename, 'r')
        self.table, self.tags, self.data = [],[],[]
        tabling = False
        table = None
        for l in f.readlines():
            w = l.split()
            if len(w) == 0 or w[0][0] == '#':
                continue
            if not tabling:
                if table != None:
                    self.table.append(array(table))
                self.tags.append(w[0])
                self.data.append(w[1:])
                tabling = True
                table = []
            else:
                table.append([int(x) for x in w])
                tabling = len(table) < n_rows
        if table != None:
            self.table.append(array(table))

    def store(self, tag, table, data=None):
        f = open(self.filename, 'a')
        f.write('%i' % tag)
        if data != None:
            f.write(' ' + ' '.join(['%i' %x for x in data]))
        f.write('\n')
        for row in table:
            f.write(' '.join('%5i' % x for x in row) + '\n')

class tableState:
    def store(self, m):
        biases = m.read('ac', 'on_bias'), m.read('ac', 'off_bias'), \
            m.read('rca', 'servo_mode')[:8], m.read('rca', 'data_mode')[:1]
        self.data = biases
        self.nrow = len(biases[0])

    def restore(self, m, lp_init=True):
        biases = self.data
        # Restore SQ1 and servoing
        m.write('ac', 'on_bias', biases[0])
        m.write('ac', 'off_bias', biases[1])
        time.sleep(0.01)
        m.write('rca', 'servo_mode', biases[2])
        m.write('rca', 'data_mode', biases[3])
        if lp_init:
            m.write('rca', 'flx_lp_init', [1])
        time.sleep(0.1)

    def servo_mode(self, m):
        m.write('rca', 'servo_mode', [0]*8)
        m.write('rca', 'data_mode', [0])
        m.write('ac', 'on_bias', [0]*self.nrow)
        m.write('ac', 'off_bias', [0]*self.nrow)
        time.sleep(0.01)
        

if __name__ == '__main__':
    import time
    from optparse import OptionParser
    import interservo

    o = OptionParser()
    o.add_option('--create', action='store_true')
    o.add_option('--record', action='store_true')
    o.add_option('--no-storage', action='store_true')
    o.add_option('--store')
    o.add_option('--recall')
    o.add_option('--linear', type='int')
    opts, args = o.parse_args()

    m = mce()
    n_col = 16
    n_row = 33
    
    SQ2_DAC = 16384
    quanta = interservo.expt_param('sq2_flux_quanta', dtype='int')
    _q = array(quanta)
    _q[_q==0] = SQ2_DAC
    quanta = _q * (SQ2_DAC / _q)

    filename = args[0]
    fbData = sq2fbFile(filename, new=opts.create, n_rows=n_row)

    if opts.recall != None:
        print list(fbData.tags)
        data = fbData.table[list(fbData.tags).index(opts.recall)]
        interservo.write_sq2_all(m, data)
        sys.exit(0)

    if opts.linear != None:
        # Load adjustment slopes
        slopes = array([ float(x) for x in open(filename, 'r').read().split()])
        #print slopes
        #print slopes.shape
        #print float(opts.linear)
        #print (slopes * float(opts.linear)).shape
        #print quanta
        # Load tes=0 sq2_fb from experiment.cfg
        c_rows = interservo.expt_param('array_width', dtype='int')[0]
        fb = array(interservo.expt_param('sq2_fb_set', dtype='int'))
        fb = fb.reshape(-1, c_rows).transpose()[:n_row,:n_col]
        #print fb.shape
        slopes = slopes.reshape((-1,n_col))
        #print slopes
        #print (fb+ slopes*float(opts.linear)).shape
        fb = ((fb + slopes * float(opts.linear)) % quanta).astype('int')
        #print fb.shape
        interservo.write_sq2_all(m, fb)
        sys.exit(0)

    # Turn off servoing and SQ1
    state = tableState()
    state.store(m)
    state.servo_mode(m)

    if opts.create or opts.no_storage:
        steps = 20
    else:
        steps = 10
    # Re-servo the SQ2
    fb_in = interservo.read_sq2_all(m, n_row, n_col)
    if not opts.create:
        fb0_1 = fbData.table[-1]
        interservo.write_sq2_all(m, fb0_1)
    interservo.reservo_all(m, steps=steps, quanta=quanta)
    # Get new fb array
    fb0_2 = interservo.read_sq2_all(m, n_row, n_col)
    # Store new array
    tag = 0
    if opts.store != None:
        tag = int(opts.store)
    if not opts.no_storage:
        fbData.store(tag, fb0_2)

    # If we're active, get the difference between new and last FB arrays:
    if not opts.create:
        fb0_1 = fbData.table[-1]
        print 'Mean shift: ', mean(fb0_2 - fb0_1, axis=0)
        fb_out = fb_in + fb0_2 - fb0_1
    else:
        fb_out = fb_in
    interservo.write_sq2_all(m, fb_out)

    state.restore(m)
        
        
    
