import os
import auto_setup.util as util
from numpy import *
from mce_data import MCERunfile, MCEFile

import servo

def go(tuning, rc, filename=None, fb=None, slope=None, bias=None, gain=None):

    ok, servo_data = acquire(tuning, rc, filename=filename, fb=fb,
                             bias=bias, gain=gain)
    if not ok:
        raise RuntimeError, servo_data['error']

    lock_points = reduce(tuning, servo_data, slope=slope)
    plot(tuning, servo_data, lock_points)

    # Return dictionary of relevant results
    return {'sq2_target': lock_points['lock_y']}


def acquire(tuning, rc, filename=None, fb=None,
            bias=None, gain=None):

    # Convert to 0-based rc indices.
    rci = rc - 1

    # File defaults
    if filename == None:
        filename, acq_id = tuning.get_filename(rc=rc, action='ssa')
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Biasing semantics are complicated, fix me.
    change_bias = not (bias == False)
    if bias == None and tuning.get_exp_param('sq2_servo_bias_ramp')[0] != 0:
        bias = {}
        for k in ['start','count','step']:
            bias[k] = tuning.get_exp_param('sq2_servo_bias_%s'%k)[0]
    if bias == None or bias == False:
        bias = {'start': tuning.get_exp_param('default_sq2_bias'),
                'count': 1,
                'step': 0 }
    # FB
    if fb == None:
        fb = {}
        for k in ['start','count','step']:
            fb[k] = tuning.get_exp_param('sq2_servo_flux_%s'%k)[0]
    if gain == None:
        gain = tuning.get_exp_param('sq2servo_gain')[rci]
    
    # Execute C servo program
    cmd = [tuning.bin_path+'/sq2servo', filename,
           bias['start'], bias['step'], bias['count'],
           fb['start'], fb['step'], fb['count'],
           rc, int(change_bias), gain]

    status = tuning.run(cmd)
    if status != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.data_dir, filename)
    rf = MCERunfile(fullname)
    n_frames = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2] * \
        rf.Item('par_ramp', 'par_step loop2 par1', type='int')[2]
    
    util.register(acq_id, 'tune_servo', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename':fullname }


def reduce(tuning, sq2file, lock_amp=True, slope=None):
    # Defaults from config file
    if slope == None:
        slope = tuning.get_exp_param('sq2servo_gain')[rci] / \
            tuning.get_exp_param('sq1servo_gain')[rci]
    if not hasattr(sq2file, 'haskey'):
        sq2file = {'filename': sq2file,
                   'basename': os.path.split(sq2file)[-1]}

    datafile = sq2file['filename']
    rf = MCERunfile(datafile+'.run')
    error, feedback = util.load_bias_file(datafile+'.bias')

    # How many biases is this?
    n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2]
    fb_params = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
    fb_0, d_fb, n_fb = fb_params
    fb = arange(fb_0, n_fb*d_fb+fb_0, d_fb)

    # Assert n_bias * n_fb == feedback.shape[1]

    # Analyze each bias independently
    for ib in range(n_bias):
        # The signal we will look at
        y = feedback[:,ib*n_fb:(ib+1)*n_fb]
        a = servo.get_lock_points(y, scale=n_fb/40, yscale=4000, lock_amp=lock_amp, slope=slope)

    # Add feedback keys
    for k in ['lock', 'left', 'right']:
        a[k+'_x'] = fb[a[k+'_idx']]
    return a

def plot(tuning, servo_data, lock_points, plot_file=None, format='pdf'):

    if not hasattr(servo_data, 'haskey'):
        servo_data = {'filename': servo_data,
                   'basename': os.path.split(servo_data)[-1]}

    if plot_file == None:
        _, basename = os.path.split(servo_data['filename'])
        plot_file = os.path.join(tuning.plot_dir, '%s.%s' % (basename, format))

    datafile = servo_data['filename']
    rf = MCERunfile(datafile+'.run')
    error, servo_val = util.load_bias_file(datafile+'.bias')

    # How many biases is this?
    n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2]
    fb_params = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
    fb_0, d_fb, n_fb = fb_params
    fb = arange(fb_0, n_fb*d_fb+fb_0, d_fb)
    
    # What columns are these?
    rcs = rf.Item('FRAMEACQ', 'RC', type='int')
    channels = [(int(rc)-1)*8 + i for i in range(8) for rc in rcs]

    # Plot plot plot
    servo.plot(fb, servo_val, lock_points, plot_file,
               title=servo_data['basename'],
               titles=['Column %i' %c for c in channels],
               xlabel='SQ2 FB / 1000',
               ylabel='SA FB / 1000')
