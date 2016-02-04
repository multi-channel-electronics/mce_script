# vim: ts=4 sw=4 et
import util
import series_array
import sq2_servo
import sq1_servo
import sq1_ramp
import frame_test
import mux11d

import os
import time
import shutil
from numpy import *


def do_init(tuning, rcs, check_bias, ramp_sa_bias, note):
    # write a note file
    if (note != None):
        tuning.write_note(note)

    # initialise the squid tuning results file
    tuning.write_sqtune(rcs=rcs, append=False)

    # Check the MCE initialization state -- in case of recent power
    # cycle.
    tuning.run(["mce_check_init", "-q"])

    # check whether the SSA and SQ2 biases have already been set
    on_bias = False
    if (check_bias):
        if str(rcs[0]) == "s":
            check_rcs = tuning.rc_list()
        else:
            check_rcs = rcs
		
        for c in check_rcs:
            exit_status = tuning.run(["check_zero", "rc%i" % (c), "sa_bias"])
            if (exit_status > 8):
                print "check_zero failed with code", exit_status
            on_bias += exit_status

    # experiment.cfg setting may force a ramp_sa_bias.
    if (ramp_sa_bias == None):
        ramp_sa_bias = tuning.get_exp_param("sa_ramp_bias")

    if (tuning.get_exp_param("tes_bias_do_reconfig") != 0):
        # setting detectors bias by first driving them normal and then
        # to the transition.
        cfg_tes_bias_norm = tuning.get_exp_param("tes_bias_normal")
        for i,x in enumerate(cfg_tes_bias_norm):
            tuning.cmd("wra tes bias %i %s" % (i, x))

        time.sleep(tuning.get_exp_param("tes_bias_normal_time"))

        cfg_tes_bias_idle = tuning.get_exp_param("tes_bias_idle")
        tuning.set_exp_param("tes_bias", cfg_tes_bias_idle)
        for i,x in enumerate(cfg_tes_bias_idle):
            tuning.cmd("wra tes bias %i %s" % (i, x))

    # Load squid biases from config file default parameters
    sa_bias = tuning.get_exp_param("default_sa_bias")
    sq2_bias = tuning.get_exp_param("default_sq2_bias")
    sq1_bias = tuning.get_exp_param("default_sq1_bias")
    sq1_bias_off = tuning.get_exp_param("default_sq1_bias_off")

    if 0:
        # Set SA and SQ2 to default biases
        tuning.copy_exp_param("default_sa_bias", "sa_bias")
        tuning.copy_exp_param("default_sq2_bias", "sq2_bias")

        # Set SQ1 off
        tuning.clear_exp_param("sq1_bias")
        tuning.clear_exp_param("sq1_bias_off")

        # if the ssa and sq2 biases were previously off the system waits for
        # thermalisation

        if (check_bias and on_bias == 0):
            print "Waiting for thermalization."
            time.sleep(tuning.get_exp_param('tuning_therm_time'))

    return {'ramp_sa_bias': ramp_sa_bias, 'sq1_bias': sq1_bias,
            'sq1_bias_off': sq1_bias_off, 'sq2_bias': sq2_bias,
            'sa_bias': sa_bias, 'sa_bias_cold': (on_bias==0)}

def set_basic_mce_params(tuning,
                         servo_mode=1,
                         flux_jumping=0,
                         data_mode=0,
                         adc_offset_all=None,
                         run_now=False):
    """
    Helper function to set a few common parameters.
    """
    tuning.set_exp_param("servo_mode", servo_mode)
    tuning.set_exp_param("flux_jumping", flux_jumping)
    tuning.set_exp_param("data_mode", data_mode)

    if not adc_offset_all is None:
        tuning.set_exp_param("config_adc_offset_all", int(adc_offset_all))

    if run_now:
        tuning.write_config(run_now=run_now)


#  do_*
#  
#  These functions execute a stage of the tuning.  Each is structured
#  in the same way; first the MCE is configured so that the spawned
#  program can do the work.  Then the ramper or servoer is spawned and
#  the data analyzed.  The results of the analysis are then used to
#  update the experiment.cfg file and MCE with new set/lock points.

def prepare_sa_ramp(tuning, tune_data, cols=None):
    """
    Prepare the MCE to run the SA ramp.
    """
    # Get columns relevant to this tuning
    if cols == None:
        cols = array(tuning.column_list())
    
    set_basic_mce_params(tuning, adc_offset_all=0)

    # Also zero out the per-column ADC offsets.
    tuning.set_exp_param_range("adc_offset_c", cols, cols*0)

    # Set SQ2 and SQ1 biases to 0
    tuning.set_exp_param_range("sq2_bias", cols, cols*0)
    tuning.clear_exp_param('sq1_bias')
    tuning.clear_exp_param('sq1_bias_off')

    # Set the SA bias and offset to the default values
    offset_ratio = tuning.get_exp_param("sa_offset_bias_ratio")
    def_sa_bias = tune_data['sa_bias']
    def_sa_offset = (def_sa_bias * offset_ratio).astype('int')
    tuning.set_exp_param_range("sa_bias", cols, def_sa_bias[cols])
    tuning.set_exp_param_range("sa_offset", cols, def_sa_offset[cols])

    # Make sure that, in mux11d mode, we aren't muxing the SA FB
    is_mux11d = tuning.get_exp_param("hardware_mux11d", 0) == 1
    if is_mux11d:
        tuning.set_exp_param('config_fast_sa_fb', 0)
        tuning.set_exp_param('config_fast_sq1_bias', 0)

        is_hybrid = \
          tuning.get_exp_param('mux11d_hybrid_row_select',missing_ok=True) == 1
        if is_hybrid:
            # May want to be more surgical ; but for now, since
            # hybridization could include BC RSes, need to make sure
            # these aren't being switched ; for now fix to zero.
            n_rs = len(tuning.get_exp_param('row_select'))
            tuning.set_exp_param('row_select', [0]*n_rs)
            tuning.set_exp_param('row_deselect', [0]*n_rs)

    # Update settings.
    tuning.write_config()

def do_sa_ramp(tuning, rc, rc_indices, ramp_sa_bias=False, write_default=False):

    # Acquire
    ok, ramp_data = series_array.acquire(tuning, rc,
                                         do_bias=ramp_sa_bias)
    if not ok:
        raise RuntimeError, ramp_data['error']

    sa = series_array.SARamp(ramp_data['filename'], tuning=tuning)
    bias_ramp = sa.bias_style == 'ramp'

    # If multi-bias, plot each one.
    if bias_ramp and tuning.get_exp_param('tuning_do_plots'):
        plot_out = sa.plot()
        tuning.register_plots(*plot_out['plot_files'])

    if bias_ramp:
        sa.reduce1()
        sa_summary = sa.ramp_summary()
        if tuning.get_exp_param('tuning_do_plots'):
            sa_summary.plot()
        sa = sa.select_biases() # replace with best bias version

    lock_points = sa.reduce()
    
    # Set-point results for feedback and ADC_offset
    fb, target = lock_points['lock_x'], lock_points['lock_y']
    tuning.set_exp_param_range("adc_offset_c", rc_indices, target.astype('int'))

    # Remove flux quantum to bring SA FB into DAC range.
    q = tuning.get_exp_param("sa_flux_quanta")[rc_indices]
    q[q<=0] = 65536
    tuning.set_exp_param_range("sa_fb", rc_indices, fb % q)

    # Maybe the bias and SA offset, too.
    if ramp_sa_bias:
        offset_ratio = tuning.get_exp_param('sa_offset_bias_ratio')
        tuning.set_exp_param_range("sa_bias", rc_indices, sa.bias)
        tuning.set_exp_param_range("sa_offset", rc_indices,
                                   (offset_ratio * sa.bias).astype('int'))
        if write_default:
            tuning.copy_exp_param("sa_bias","default_sa_bias")

    tuning.write_config()

    # Plot final bias result
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sa.plot()
        tuning.register_plots(*plot_out['plot_files'])

    return {'status': 0, 'column_adc_offset': target, 'sq_data': sa}


def prepare_sq2_servo(tuning, tune_data, cols=None):
    """
    Prepare the MCE to run the SQ2 servo.
    """
    # Get columns relevant to this tuning
    if cols == None:
        cols = array(tuning.column_list())

    # Be sure to restore per-column adc_offset.
    set_basic_mce_params(tuning, adc_offset_all=0)

    # Set SQ1 biases to 0
    tuning.clear_exp_param('sq1_bias')
    tuning.clear_exp_param('sq1_bias_off')

    # Set SQ2 bias from tune_data.
    tuning.set_exp_param_range('sq2_bias', cols, tune_data['sq2_bias'][cols])

    # Update settings.
    tuning.write_config()

def do_sq2_servo(tuning, rc, rc_indices, write_default=False):
    # Sets the initial SA fb (found in the previous step or set to mid-range)
    # for the SQ2 servo
    sa_fb_init = tuning.get_exp_param('sa_fb')
    f = open(os.path.join(tuning.base_dir, "safb.init"), "w")
    for x in sa_fb_init:
        f.write("%i\n" % x)
    f.close()

    # Update settings, acquire servo
    tuning.write_config()
    ok, servo_data = sq2_servo.acquire(tuning, rc)
    if not ok:
        raise RuntimeError, servo_data['error']

    sq = sq2_servo.SQ2Servo(servo_data['filename'], tuning=tuning)
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

    sq2_data = sq.reduce()

    # Plot final bias result
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])
        if bias_ramp:
            rs = sq.ramp_summary()
            plot_out = rs.plot()
            tuning.register_plots(*plot_out['plot_files'])

    # Save SQ2 set-point (SA feedback) and SQ2 feedback
    q = tuning.get_exp_param("sa_flux_quanta")[rc_indices]
    q[q<=0] = 65536
    tuning.set_exp_param_range("sa_fb", rc_indices,
        sq2_data["lock_y"].astype(int) % q)
    tuning.set_exp_param_range("sq2_fb", rc_indices, sq2_data["lock_x"])

    # Write the sq2 bias choice too?
    if bias_ramp:
        tuning.set_exp_param_range("sq2_bias", rc_indices, sq.bias)
        if write_default:
            tuning.copy_exp_param("sq2_bias", "default_sq2_bias")

    # For SQ2 fast-switching, write the big FB array
    tu_nr = tuning.get_exp_param('default_num_rows') # number of rows
    fb_nr = tuning.get_exp_param('array_width') # number of rows in sq2_fb_set
    fb_set = tuning.get_exp_param('sq2_fb_set').reshape(-1, fb_nr).transpose()
    fb_set[:tu_nr,rc_indices] = sq2_data['lock_x']
    tuning.set_exp_param('sq2_fb_set', fb_set.transpose().ravel())

    tuning.write_config()
    return {'status': 0, 'sq_data': sq}


def prepare_sq1_servo(tuning, tune_data):
    """
    Prepare the MCE to run the SQ1 servo.
    """
    # Use the per-column adc_offset values.
    set_basic_mce_params(tuning, adc_offset_all=0)

    # Enable SQ1 bias
    tuning.set_exp_param('sq1_bias', tune_data['sq1_bias'])
    tuning.set_exp_param('sq1_bias_off', tune_data['sq1_bias_off'])

    tuning.write_config()


def do_sq1_servo(tuning, rc, rc_indices, write_default=False):
   
    # super_servo means collecting all-row servo data for fast sq2 switching
    fast_sq2 = tuning.get_exp_param('config_fast_sq2')
    super_servo = fast_sq2 or tuning.get_exp_param('sq1_servo_all_rows')
    
    if super_servo and not fast_sq2:
        ok, servo_data = sq1_servo.acquire_all_row_painful(tuning, rc)
    else:
        ok, servo_data = sq1_servo.acquire(tuning, rc, super_servo=super_servo)

    if not ok:
        raise RuntimeError, servo_data['error']

    sq = sq1_servo.SQ1Servo(servo_data['filename'], tuning=tuning)
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

    sq1_data = sq.reduce()
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])
        if bias_ramp:
            rs = sq.ramp_summary()
            plot_out = rs.plot()
            tuning.register_plots(*plot_out['plot_files'])

    # Load existing FB choices
    fb_nr = tuning.get_exp_param('array_width') # number of rows in sq2_fb_set
    fb_col = tuning.get_exp_param('sq2_fb')
    fb_set = tuning.get_exp_param('sq2_fb_set').reshape(-1, fb_nr).transpose() # r,c
    
    # Determine the SQ2 FB for each column, and if possible for each detector.
    cols = sq.cols
    phi0 = tuning.get_exp_param('sq2_flux_quanta')[cols]
    phi0[phi0<=0] = 65536 # kill empty flux_quanta
    if super_servo:
        n_row, n_col = sq.data_shape[-3:-1]
        fb_set[:n_row,cols] = sq1_data['lock_y'].reshape(-1, n_col) % phi0
        # Get chosen row on each column
        rows = tuning.get_exp_param('sq2_rows')[cols]
        fb_col[cols] = array([ fb_set[r,c] for r,c in zip(rows, cols) ]) % phi0
    else:
        # Analysis gives us SQ2 FB for chosen row of each column.
        fb_col[cols] = sq1_data['lock_y'] % phi0
        n_row = tuning.get_exp_param("default_num_rows")
        fb_set[:,cols] = sq1_data['lock_y'] % phi0

    # Write the sq1 bias choice too?
    if bias_ramp:
        tuning.set_exp_param("sq1_bias", sq.bias)
        if write_default:
            tuning.copy_exp_param("sq1_bias", "default_sq1_bias")

    # Save results, but remove flux quantum
    tuning.set_exp_param('sq2_fb', fb_col)
    tuning.set_exp_param('sq2_fb_set', fb_set.transpose().ravel())

    tuning.write_config()
    return {'status': 0, 'sq_data': sq}


def prepare_sq1_ramp(tuning, ramp_check=False):
    """
    Prepare the MCE to run the SQ1 servo.
    """
    # Set up the per-column adc_offset values, unless this is the ramp_check
    set_basic_mce_params(tuning, adc_offset_all=int(ramp_check))
    tuning.write_config()


def do_sq1_ramp(tuning, rcs, init=True, ramp_check=False):
    # Don't correct for sample_num!
    samp_num = tuning.get_exp_param("default_sample_num")
    array_width = tuning.get_exp_param("array_width")

    # Acquire ramp for each RC
    ramps = []
    for rc in rcs:
        ok, info = sq1_ramp.acquire(tuning, rc, check=ramp_check)
        if not ok:
            raise RuntimeError, 'sq1ramp failed for rc%s (%s)' % \
                (str(rc), info['error'])
        ramps.append(sq1_ramp.SQ1Ramp(info['filename']))

    # Join into single data/analysis object
    #... something is wrong here ...
    ramps = sq1_ramp.SQ1Ramp.join(ramps)
    ramps.tuning = tuning
    lock_points = ramps.reduce()
    n_row, n_col = ramps.data_shape[-3:-1]

    # Save new ADC offsets
    adc_col = tuning.get_exp_param('adc_offset_c')[ramps.cols].reshape(1,-1)
    adc_adj = (lock_points['lock_y']). \
        reshape(n_row, n_col).astype('int')
    new_adc = adc_col + adc_adj

    # Careful with index transposition here
    cv, rv = ix_(ramps.cols, ramps.rows)
    idx = (array_width * cv + rv).ravel()
    adc = tuning.get_exp_param('adc_offset_cr')
    adc[idx] = new_adc.transpose().ravel()

    # Sometimes we don't actually want to change anything
    if not ramp_check:
        # Note that adc_offset_cr needs to be corrected for samp_num
        tuning.set_exp_param('adc_offset_cr', adc/samp_num)
        tuning.set_exp_param('config_adc_offset_all', 1)
        tuning.write_config()

    # Produce plots
    masks = util.get_all_dead_masks(tuning)
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = ramps.plot(dead_masks=masks)
        try:
            tuning.register_plots(*plot_out['plot_files'])
        except:
            tuning.log.write('plot_reg failed because plot_out = %s\n' % str(plot_out))
        ramps.plot(dead_masks=masks)


    # Return analysis stuff so it can be stored in .sqtune...
    return {'status': 0, 'sq_data': ramps}


def do_sq1_ramp_tes(tuning, rcs, init=True):
    # Just make sure we're in open-loop
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.write_config()

    # Acquire ramp for each RC
    ramps = []
    for rc in rcs:
        ok, info = sq1_ramp.acquire_tes_ramp(tuning, rc)
        if not ok:
            raise RuntimeError, 'sq1ramp failed for rc%s (%s)' % \
                (str(rc), info['error'])
        ramps.append(sq1_ramp.SQ1RampTes(info['filename']))

    # Join into single data/analysis object
    ramps = sq1_ramp.SQ1RampTes.join(ramps)
    ramps.tuning = tuning
    lock_points = ramps.reduce()

    # Produce plots
    masks = util.get_all_dead_masks(tuning)
    if tuning.get_exp_param('tuning_do_plots'):
        ramps.plot(dead_masks=masks)

    # Return analysis stuff so it can be stored in .sqtune...
    return {'status': 0, 'sq_data': ramps}


def operate(tuning):
    """
    Mask dead detectors, enable the MCE servo, and set the default data mode.

    This should be run once the final ADC offsets have been chosen (sq1_ramp).
    """
    # Servo control
    tuning.set_exp_param('servo_mode', 3)
    for param in ['servo_p', 'servo_i', 'servo_d', 'flux_jumping',
                  'data_mode']:
        tuning.copy_exp_param('default_%s'%param, param)

    # Compile dead detector mask
    print "Assembling dead detector mask."
    mask = util.get_all_dead_masks(tuning, union=True)
    if mask != None:
      tuning.set_exp_param("dead_detectors", mask.data.transpose().reshape(-1))

    print "Assembling frail detector mask."
    mask = util.get_all_dead_masks(tuning, union=True, frail=True)
    if mask != None:
      tuning.set_exp_param("frail_detectors", mask.data.transpose().reshape(-1))

    # Write to MCE
    tuning.write_config(run_now=True)



def frametest_check(tuning, rcs, row, column):
    """
    Fix me.
    """
    # Permit row override, or else take it from config
    if (row == None):
        row = 9
        print "Row = %i is used for frametest_plot by default." % row

    if (len(rcs) < 4):
        for rc in rcs:
            lock_file_name, acq_id = tuning.filename(rc=rc, action="lock")
            frametest_plot(lock_file_name, column=column, row=row, rc=rc,
                    binary=1, acq_id=acq_id)
    else:
        lock_file_name, acq_id = tuning.filename(rc="s", action="lock")
        rc = 5
        frametest_plot(lock_file_name, column=column, row=row, rc=rc,
                binary=1, acq_id=acq_id)


def auto_setup(rcs=None, check_bias=None, short=False, ramp_sa_bias=None,
               note=None, reg_note=None, data_dir=None,
               first_stage=None, last_stage=None,
               debug=False):
    """
Run a complete auto setup.

This metafunction runs, in turn, each of acquisition, tuning, and reporting
functions to perform an entire auto setup procedure, exactly like the old
IDL auto_setup_squids."""

    tuning = util.tuningData(data_dir=data_dir, reg_note=reg_note, debug=debug)
    print 'Tuning ctime: %i' % tuning.the_time
    print 'Tuning date : ' + tuning.date

    # Create data and analysis directories
    tuning.make_dirs()
    shutil.copy2(tuning.exp_file, tuning.data_dir)

    # Register plots for offload
    tuning.register_plots(init=True)

    # set rc list, if necessary
    if (rcs == None):
        print "  Tuning all available RCs."
        rcs = ['s']

    # default parameters
    if ramp_sa_bias == None:
        ramp_sa_bias = bool(tuning.get_exp_param('sa_ramp_bias'))
    if check_bias == None:
        check_bias = bool(tuning.get_exp_param('tuning_check_bias'))
    write_default_bias = bool(tuning.get_exp_param('write_default_bias',
        missing_ok = 1, default = 0))
    
    # initialise the auto setup
    tune_data = do_init(tuning, rcs, check_bias, ramp_sa_bias, note)

    if (tune_data == None):
        return 1

    if tuning.get_exp_param("hardware_mux11d") == 1:
        # mux11d tuning
        stages = ['sa_ramp',
                  'rs_servo',
                  'sq1_servo_sa',
                  'sq1_ramp',
                  'sq1_ramp_check',
                  'sq1_ramp_tes',
                  'operate']
        mux11d.do_init_mux11d(tuning,tune_data)
    else:
        # Standard tuning
        stages = ['sa_ramp',
                  'sq2_servo',
                  'sq1_servo',
                  'sq1_ramp',
                  'sq1_ramp_check',
                  'sq1_ramp_tes',
                  'operate']
        
    if first_stage == None:
        if short == 1:
            first_stage = 'sq1_servo'
        if short == 2:
            first_stage = 'sq1_ramp'
    if first_stage == None:
        first_stage = stages[0]
    if last_stage == None:
        if (tuning.get_exp_param("stop_after_sq1_servo") == 1):
            last_stage = 'sq1_servo'
    if last_stage == None:
        last_stage = stages[-1]

    s0, s1 = stages.index(first_stage), stages.index(last_stage)
    stages = stages[s0:s1+1]

    # ramp tes bias and see open loop response?
    if tuning.get_exp_param("sq1_ramp_tes_bias") == 0 or short != 0:
        if 'sq1_ramp_tes' in stages:
            stages.remove('sq1_ramp_tes')

    # skip sq1 ramp check unless requested:
    if tuning.get_exp_param("sq1_ramp_check", missing_ok = True,
            default = 1) == 0:
        if 'sq1_ramp_check' in stages:
            stages.remove('sq1_ramp_check')

    if len(rcs) != 1:
        raise RuntimeError, \
            "Tuning of misc. RCs no longer supported.  Pick a single RC, or use RCS."
    else:
        # This indentation left in for clarity of commit diff.  Remove me some day.
        c = rcs[0]
        print "Processing rc%s" % str(c)
        if c == 's':
            rc_indices = array(tuning.column_list())
        else:
            rc_indices = 8 * (int(c) - 1) + arange(8)
        if 'sa_ramp' in stages:
            prepare_sa_ramp(tuning, tune_data, cols=rc_indices)
            sa_dict = do_sa_ramp(tuning, c, rc_indices,
                                 ramp_sa_bias=ramp_sa_bias,
                                 write_default=write_default_bias)
            tuning.write_sqtune(sq_data=sa_dict['sq_data'])
        if 'sq2_servo' in stages:
            prepare_sq2_servo(tuning, tune_data, cols=rc_indices)
            s2_dict = do_sq2_servo(tuning, c, rc_indices,
                                   write_default=write_default_bias)
            tuning.write_sqtune(sq_data=s2_dict['sq_data'])
            if (s2_dict["status"] != 0):
                return s2_dict["status"]
        if 'sq1_servo' in stages:
            prepare_sq1_servo(tuning, tune_data)
            s1_dict = do_sq1_servo(tuning, c, rc_indices,
                                   write_default=write_default_bias)
            tuning.write_sqtune(sq_data=s1_dict['sq_data'])
            if (s1_dict["status"] != 0):
                return s1_dict["status"]

    if 'rs_servo' in stages:
        rs = mux11d.do_rs_servo(tuning, rcs, tune_data)

    if 'sq1_servo_sa' in stages:
        sq1 = mux11d.do_sq1_servo_sa(tuning, rcs, tune_data)

    if 'sq1_ramp' in stages:
        # sq1 ramp
        prepare_sq1_ramp(tuning)
        sq1_dict = do_sq1_ramp(tuning, rcs)
        tuning.write_sqtune(sq_data=sq1_dict['sq_data'])

    if 'sq1_ramp_check' in stages:
        # sq1 ramp check
        prepare_sq1_ramp(tuning, ramp_check=True)
        sq1_dict = do_sq1_ramp(tuning, rcs, ramp_check=True)
        tuning.write_sqtune(sq_data=sq1_dict['sq_data'],
                            block='SQUID_SQ1_RAMPC')

    if 'sq1_ramp_tes' in stages:
        # open-loop ramping of the TES bias
        prepare_sq1_ramp(tuning, ramp_check=True)
        tes = do_sq1_ramp_tes(tuning, rcs)

    if 'frametest' in stages:
        # lock check
        print 'frametest_check to-be-implemented...'
        #frametest_check(tuning, rcs, row, column)

    if 'operate' in stages:
        # Enable servo
        operate(tuning)

    # Copy experiment.cfg and config script between main data dir and tuning dir.
    shutil.copy2(tuning.config_mce_file, os.path.join(tuning.data_dir,
                 "config_mce_auto_setup_" + tuning.date))
    shutil.copy2(tuning.exp_file, tuning.data_dir)

    t_elapsed = time.time() - tuning.the_time
    print "Tuning complete.  Time elapsed: %i seconds." % t_elapsed
    return 0
