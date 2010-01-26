#!/usr/bin/python

import sys, commands
from mce_data import *
from pylab import *
from numpy import *

def run(x):
    return commands.getoutput(x)


def doFile(filename, samples=None):
    # Open said data
    f = MCEFile(filename)
    d = f.Read()
    
    col = d.channels[0]
    adc_offset = array(f.runfile.Item2dRC('HEADER', 'RB rc%i adc_offset%%i',
                                          type='int', rc_count=2))[col,:]
    row_len = f.runfile.Item('HEADER', 'RB rc%i row_len' % (col/8+1),
                             array=False, type='int')
    num_rows = f.runfile.Item('HEADER', 'RB cc num_rows',
                              array=False, type='int')
    print row_len
    if samples == None:
        samples = arange(0, row_len*num_rows)

    # Plot
    plot(d.data[0,samples])
    for r in arange(amin(samples/row_len), max(samples/row_len)):
        plot([r*row_len, (r+1)*row_len], [adc_offset[r], adc_offset[r]])
    show()

args = sys.argv[1:]
for a in args:
    try:
        col = int(a)
        rc, ch = col/8 +1, col % 8

        # Acquire 1 col data
        text = run('mce_raw_acq_1col %i %i' % (rc, ch))
        filename = text.split()[4]
        print 'Acquired %s' % filename
    except ValueError:
        filename = a
        print 'Loading %s' % filename
    
    doFile(filename)
