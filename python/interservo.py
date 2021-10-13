#!/usr/bin/python
# vim: ts=4 sw=4 et

from __future__ import division
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import range
from past.utils import old_div
from auto_setup.util import mas_path

## This is an old script... is it still in use?  We should at least
## stop using the swig-based wrapper.
#from mce import *
from pymce.compat import old_mce as mce

from mce_data import *
from glob import glob
import sys, subprocess
from numpy import *
import optparse

N_RC=2
NCOLS=N_RC*8
rc_present = None

def expt_param(key, dtype=None):
    src = mas_path().experiment_file()
    line = subprocess.getoutput('mas_param -s %s get %s' % (src, key)).rstrip()
    s = line.split(' ')
    if dtype is None or dtype == 'string':
        return s
    if dtype == 'int':
        return [ int(ss) for ss in s if ss != '']
    if dtype == 'float':
        return [ float(ss) for ss in s if ss != '']
    raise ValueError('can\'t handle dtype=\'%s\' '%dtype)


def reservo(m, param, gains=None, rows=None, steps=None, verbose=False):
    done = False
    if rows is None:
        rows = [0]*NCOLS
    if gains is None:
        gains = [0.02]*NCOLS
    # Setup a default exit condition...
    if steps is None:
        steps = 1
    count = 0
    while not done:
        data = m.read_frame(data_only=True)
        dy = [data[NCOLS*r + c] for (c,r) in enumerate(rows)]
        if verbose:
            print('Measured: ', dy)
        dx = [g*d for d,g in zip(dy, gains)]
        x = m.read(param[0], param[1])
        x_new = [int(a+b) for (a,b) in zip(x,dx)]
        if verbose:
            print('Applied: ', x_new)
        m.write(param[0], param[1], x_new)
        if steps is not None:
            count += 1
            if count >= steps:
                done = True

def set_adcoffset(m, ofs):
    for rc in [1]:  #range(4):
        for c in range(8):
            m.write('rc%i'%(rc+1), 'adc_offset%i'%c,
                      [ofs[rc*8+c]]*41)

def get_historical_offset(folder, stage='ssa', rows=None):
    offsets = []
    if rows is None:
        rows = [0]*NCOLS
    for rc in range(N_RC):
        file = glob(folder+'/*RC%i_%s.run'%(rc+1,stage))
        rf = MCERunfile(file[0])
	all_offsets = rf.Item2d('HEADER', 'RB rc%i adc_offset%%i'%(rc+1),
                              	type='int')
        offsets.extend([all_offsets[c][r] for (c,r) in
                        enumerate(rows[rc*8:rc*8+8])])
    return offsets

def write_adc_offset(m, ofs, fill=True, n_rows=33):
    for c in range(N_RC*8):
        m.write('rc%i'%((old_div(c,8))+1), 'adc_offset%i'%(c%8), [ofs[c]]*41)

    
def get_line(m, rows=None):
    if rows is None:
        rows = [0]*NCOLS
    d = m.read_frame(data_only=True)
    return [d[r*NCOLS+c] for (c,r) in enumerate(rows)]

def process_options():
    opts = optparse.OptionParser(usage='Usage: %prog [options] stage\n\n' \
                                     '    stage should be one of sq1, sq2, sa')
    opts.add_option('--tuning', '-t', type='string', default=None)
    opts.add_option('--verbose', '-v', action='store_true', default=False)
    opts.add_option('--quiet', '-q', action='store_true', default=False)
    opts.add_option('--steps', '-n', type='int', default=0, \
                    help='number of servo steps to execute (default 0)')
    opts.add_option('--samples', '-s', type='int', default=10, \
                    help='number of frames to include in the before/after measurements (default 10)')
    return opts.parse_args()

def main():
    opts, args = process_options()

    if len(args) != 1:
        print('Specify exactly one stage argument')
        sys.exit(10)
    stage = args[0]

    if opts.tuning is None:
        print('Using most recent tuning...')
        try:
            data_root = mas_path().data_root()
            w = [s.strip() for s in
               open(data_root + '/last_squid_tune_name').readlines()]
            tuning = data_root + '/%s/%s/'%tuple(w)
            assert(len(glob('%s/*ssa'%tuning)) > 0)
            opts.tuning = tuning
        except:
            print('Could not find a recent tuning, or most recent tuning was ' \
                'not a full tune (specify the tuning folder manualy)!')
            sys.exit(11)

    # Get basic system description
    rc_present = expt_param('hardware_rc', dtype='int')

    if stage == 's1' or stage == 'sq1':
        # This has no analog in the tuning... sq1_fb hardware servo'd
        param = ['sq1', 'fb_const']
        g = expt_param('default_servo_i', dtype='float')
        gains = [old_div(gg,4096.) for gg in g]        
        rows = expt_param('sq2_rows', dtype='int')
    elif stage == 's2' or stage == 'sq2':
        # This is like sq1servo, but the sq1 are off
        param = ['sq2', 'fb']
        gains = expt_param('sq1_servo_gain', dtype='float')
        rows = None
    elif stage == 'sa' or stage == 'ssa':
        # This is like sq2servo, but the sq2 are off
        param = ['sa', 'fb']
        gains = expt_param('sq2_servo_gain', dtype='float')
        rows = None

    if not opts.quiet:
        print('Source tuning: %s' % opts.tuning)
        print('Servo control: %s %s' % (param[0],param[1]))
        print('Servo steps:   %i' % opts.steps)
        print('')

    # Get an mce
    m = mce()
    m.write('rca', 'data_mode', [0])
    m.write('rca', 'servo_mode', [0]*8)

    # Regardless of the stage, we can use the ADC_offset from sq2servo:
    ofs = get_historical_offset(opts.tuning, 'sq2servo')
    write_adc_offset(m, ofs)

    # Action time
    n_check = opts.samples
    n_servo = opts.steps

    # Measure initial error
    if not opts.quiet:
        err = [ get_line(m, rows) for i in range(n_check)]
        err = array(err)
        print('Initial error set (%i):' % n_check)
        print(mean(err, axis=0))

    if not opts.quiet:
        print('Servoing...')
    reservo(m, param, gains=gains, steps=n_servo, verbose=opts.verbose)

    if not opts.quiet:
        err = [ get_line(m, rows) for i in range(n_check)]
        err = array(err)
        print('Final error set (%i):' % n_check)
        print(mean(err, axis=0))

if __name__ == '__main__':
    main()
