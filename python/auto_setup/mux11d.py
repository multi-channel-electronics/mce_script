"""
__main__ style stuff for mux11d tuning.
"""

import util
import series_array
import sq2_servo
import sq1_servo
import sq1_ramp
import rs_servo
import frame_test

import os
import time
import shutil
from numpy import *

from mce_data import MCERunfile

def do_init_mux11d(tuning, tune_data):
    pass

def acquire(tuning, rc, filename=None,
            action_name='', bin_name=None):

    # File defaults
    if filename == None:
        filename, acq_id = tuning.filename(rc=rc, action=action_name)
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    cmd = [os.path.join(tuning.bin_path, bin_name), '-p', 50, rc, filename]

    status = tuning.run(cmd)
    if status != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.base_dir, filename)
    rf = MCERunfile(fullname + ".run")
    n_frames = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2] * \
        rf.Item('par_ramp', 'par_step loop2 par1', type='int')[2]
    
    tuning.register(acq_id, 'tune_servo', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename': fullname }


def do_rs_servo(tuning, rc, rc_indices):
    """
    Do necessary (but not sufficient) setup so that rsservo will
    work.  Run it, analyze, update experiment.cfg
    """

    # Load the default_row_select.  Someone has to, at some point.
    tuning.copy_exp_param('default_row_select', 'row_select')
    tuning.copy_exp_param('default_row_deselect', 'row_deselect')

    # Also load default sq1_bias and make sure it will apply in
    # fast-switching mode as well.
    sq1_bias = tuning.get_exp_param('default_sq1_bias')
    nr = tuning.get_exp_param('array_width') # number of rows sq1_bias_set
    bias_set = tuning.get_exp_param('sq1_bias_set').reshape(-1, nr).\
        transpose() # r,c
    nc = min(len(sq1_bias), bias_set.shape[1])
    bias_set[:,:nc] = sq1_bias[:nc]
    tuning.set_exp_param('sq1_bias', sq1_bias)
    tuning.set_exp_param('sq1_bias_set', bias_set.transpose().ravel())

    optimize = tuning.get_exp_param('optimize_rowsel_servo')
    if optimize == -1:
        # Don't run it, but set the SQ1 bias muxing
        tuning.set_exp_param("config_fast_sq1_bias", 1)
        tuning.write_config()
        return

    # Prepare for servo
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.copy_exp_param('default_sq1_bias', 'sq1_bias')
    tuning.copy_exp_param('default_sq1_bias_off', 'sq1_bias_off')
    tuning.set_exp_param("config_adc_offset_all", 0)
    tuning.set_exp_param("config_fast_sq1_bias", 0)
    tuning.set_exp_param("config_fast_sa_fb", 1)
    tuning.write_config()

    if len(rc) != 1:
        raise ValueError, "this module does not support weird multi-rc tunes"

    ok, servo_data = acquire(tuning, rc[0], action_name='rsservo',
                             bin_name='rs_servo')

    if not ok:
        raise RuntimeError, servo_data['error']

    sq = rs_servo.RSServo(servo_data['filename'], tuning=tuning)
    bias_ramp = sq.bias_style == 'ramp'

    # If multi-bias, plot each one.
    if bias_ramp and tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])

    if bias_ramp:
        sq.reduce1()
        sq = sq.select_biases() # best bias?

    sq_data = sq.reduce()
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])

    # Primary purpose here is to set the row select feedbacks
    new_rsel1 = sq.fb[sq_data['sel_idx_row']]
    new_rsel0 = sq.fb[sq_data['desel_idx_row']]
    if not sq.super_servo:
        n_rs = len(tuning.get_exp_param('row_select'))
        new_rsel1 = [new_rsel1[0]] * n_rs
        new_rsel0 = [new_rsel0[0]] * n_rs

    if optimize == 1:
        tuning.set_exp_param('row_select', new_rsel1)
        tuning.set_exp_param('row_deselect', new_rsel0)
        
    # Update per-det SQ1 biases with chosen values from this run
    cols = sq.cols
    if sq.bias_assoc == 'rowcol':
        new_bias = sq.bias.reshape(sq.data_shape[:2])
        bias_set[:new_bias.shape[0],cols] = new_bias
    elif sq.bias_assoc == 'col':
        # write this single bias for each column to all rows
        bias_set[:,cols] = sq.bias
    else:
        raise HowDidThisHappen

    if optimize == 1:
        tuning.set_exp_param('sq1_bias_set', bias_set.transpose().ravel())

    # Enable fast switching.
    tuning.set_exp_param("config_fast_sq1_bias", 1)

    tuning.write_config()
    return 0


def do_sq1_servo_sa(tuning, rc, rc_indices):
    """
    Do necessary (but not sufficient) setup so that sq1_servo_sa will
    work.  Run it, analyze, update experiment.cfg
    """
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
#    tuning.copy_exp_param('default_sq1_bias', 'sq1_bias')
#    tuning.copy_exp_param('default_sq1_bias_off', 'sq1_bias_off')
    tuning.set_exp_param("config_adc_offset_all", 0)
#    tuning.set_exp_param("config_fast_sq1_bias", 0)
    tuning.set_exp_param("config_fast_sa_fb", 1)
    # If we're to ramp the bias, turn off fast biasing.
    if tuning.get_exp_param("sq1_servo_bias_ramp") == 1:
        tuning.set_exp_param("config_fast_sq1_bias", 0)

    tuning.write_config()

    if len(rc) != 1:
        raise ValueError, "this module does not support weird multi-rc tunes"

    ok, servo_data = acquire(tuning, rc[0], action_name='sq1servo_sa',
                             bin_name='sq1servo_sa')

    if not ok:
        raise RuntimeError, servo_data['error']

    sq = sq1_servo.SQ1ServoSA(servo_data['filename'], tuning=tuning)
    bias_ramp = sq.bias_style == 'ramp'

    # If multi-bias, plot each one.
    if bias_ramp and tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])

    if bias_ramp:
        sq.reduce1()
        sq = sq.select_biases(assoc='rowcol') # best bias?

    sq1_data = sq.reduce()
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])


    # Load existing bias choices
    nr = tuning.get_exp_param('array_width') # number of rows sq1_bias_set
    bias_set = tuning.get_exp_param('sq1_bias_set').reshape(-1, nr).\
        transpose() # r,c

    # Update per-det SQ1 biases with chosen values from this run
    cols = sq.cols
    if sq.bias_assoc == 'rowcol':
        new_bias = sq.bias.reshape(sq.data_shape[:2])
        bias_set[:new_bias.shape[0],cols] = new_bias
    elif sq.bias_assoc == 'col':
        # write this single bias for each column to all rows
        bias_set[:,cols] = sq.bias
    else:
        raise HowDidThisHappen

    # Enable fast switching.
    tuning.set_exp_param('sq1_bias_set', bias_set.transpose().ravel())
    tuning.set_exp_param("config_fast_sq1_bias", 1)
    super_servo = tuning.get_exp_param('config_mux11d_all_rows')
    fb_set = tuning.get_exp_param('sa_fb_set').reshape(-1, nr).\
        transpose() # r,c

    fb_col = tuning.get_exp_param('sa_fb')
    
    # Determine the SA FB for each column, and if possible for each detector.
    cols = sq.cols
    phi0 = tuning.get_exp_param('sa_flux_quanta')[cols]
    phi0[phi0<=0] = 65536 # kill empty flux_quanta
    if super_servo:
        n_row, n_col = sq.data_shape[-3:-1]
        fb_set[:n_row,cols] = sq1_data['lock_y'].reshape(-1, n_col) % phi0
        # Get chosen row on each column
        rows = tuning.get_exp_param('mux11d_row_choice')[cols]
        fb_col[cols] = array([ fb_set[r,c] for r,c in zip(rows, cols) ]) % phi0
    else:
        # Analysis gives us SA FB for chosen row of each column.
        fb_col[cols] = sq1_data['lock_y'] % phi0
        n_row = tuning.get_exp_param('default_num_rows')
        fb_set[:,cols] = sq1_data['lock_y'] % phi0
        
    # Save results, but remove flux quantum
    tuning.set_exp_param('sa_fb', fb_col)
    tuning.set_exp_param('sa_fb_set', fb_set.transpose().ravel())

    tuning.write_config()
    return 0
