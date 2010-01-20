import acquire
import reduce
import report
import util
import config

import os
import subprocess
import time
from numpy import *


def step1 (directory, rc, check_bias, short, numrows, ramp_sa_bias, note):
    # directory containing data files
    os.mkdir(todays_directory + file_dir)

    # directory containing plots
    os.mkdir(todays_directory + "analysis/" + file_dir)

    c_filename = file_dir + "/" + file_dir

    if (rc == None):
        print "  No read-out cards specified; setting all available RCs."
        rc = config.rc_list(exp_config_file)

    # check whether the SSA and SQ2 biases have already been set
    on_bias = False
    if (check_bias):
        for c in rc:
            exit = subprocess.Popen(["check_zero", "rc" + c, "sa_bias"],
                    stdout=log, stderr=log).wait()

    # reset the mce
    print "mce_reset_clean suppressed!"

    # load camera defaults from experiment config file
    samp_num = config.get_exp_param(exp_config_file, "default_sample_num")
    if (numrows == None):
        numrows= config.get_exp_param(exp_config_file, "default_num_rows")

    # set this to 1 to sweep the tes bias and look at squid v-phi response.
    ramp_sq1_bias_run=config.get_exp_param(exp_config_file, "ramp_tes_bias")

    # experiment.cfg setting may force a ramp_sa_bias.
    if (ramp_sa_bias == None):
        ramp_sa_bias = config.get_exp_param(exp_config_file, "sa_ramp_bias")

    # TODO - *bias.init inputs should come from experiment.cfg
    SA_feedback_file = empty([32], dtype="int64")
    SA_feedback_file.fill(32000)

    SQ2_feedback_file = empty([32], dtype="int64")
    SQ2_feedback_file.fill(8200)

    column_adc_offset = empty([32], dtype="int64")

    if (config.get_exp_param(exp_config_file, "tes_bias_do_reconfig") != 0):
        # detector bias
        print "driving TES normal, then to idle value."

        # setting detectors bias by first driving them normal and then
        # to the transition.

        # XXX check loop limits
        cfg_tes_bias_norm = config.get_exp_param(exp_config_file,
                "tes_bias_normal")
        for i in cfg_tes_bias_norm.size():
            util.cmd("wra tes bias {0} {1}".format(i, cfg_tes_bias_norm[i]))

        time.sleep(config.get_exp_param(exp_config_file,
            "tes_bias_normal_time"))

        cfg_tes_bias_idle = config.get_exp_param(exp_config_file,
                "tes_bias_idle")
        config.set_exp_param(exp_config_file, "tes_bias", cfg_tes_bias_idle)
        for i in cfg_tes_bias_idle.size():
            util.cmd("wra tes bias {0} {1}".format(i, cfg_tes_bias_idle[i]))

    # load squid biases from config file default parameters

    def_sa_bias = config.get_exp_param(exp_config_file, "default_sa_bias")
    sq2_bias = config.get_exp_param(exp_config_file, "default_sq2_bias")
    sq1_bias = config.get_exp_param(exp_config_file, "default_sq1_bias")
    sq1_bias_off = config.get_exp_param(exp_config_file, "default_sq1_bias_off")

    # Turn flux-junmping off for tuning, though it shouldn't matter
    config.set_exp_param(exp_config_file, "flux_jumping", 0)

    # load default values into biases

    config.set_exp_param(exp_config_file, "sa_bias", def_sa_bias)
    config.set_exp_param(exp_config_file, "sq2_bias", sq2_bias)
    config.set_exp_param(exp_config_file, "sq1_bias", 0)
    config.set_exp_param(exp_config_file, "sq1_bias_off", 0)

    # Save experiment params, make config script, run it.
    status1 = util.mce_make_config(params_file=exp_config_file,
            filename=config_mce_file, run_now=1)
  
    if (status1 != 0):
        print "An error occurred running the config file"
        return 0

    # if the ssa and sq2 biases were previously off the system waits for
    # thermalisation

    if (check_bias and on_bias == 0):
        print "Waiting for thermalisation."
        time.sleep(210)

    # write a note file
    if (note != None):
        f = open(todays_directory + c_filename + "_note", "w+")
        f.write("#Note entered with SQUID autotuning data acquisition\n")
        f.write(note)
        f.write("\n")
        f.close()

    # initialise the squid tuning results file
    header_file = todays_directory + c_filename + ".sqtune"
    f = open(header_file, "w")
    f.write("<SQUID>\n<SQ_tuning_completed> 0\n<SQ_tuning_date> ")
    f.write(current_data)
    f.write("\n<SQ_tuning_dir> " + tuning.name + "\n</SQUID>\n")
    f.close()

    subprocess.call(["rm", "-f", directory + "/last_squid_tune"])
    subprocess.call(["ln", "-s", todays_folder + c_filename + ".sqtune",
        directory + "/last_squid_tune"])

    return 1


def step2and3(rc, rc_indices, file_folder, exp_config_file, def_sa_bias):
    ssa_file_name = util.filename(rc=rc, directory=file_folder)

    config.set_exp_param(exp_config_file, "data_mode", 0)
    config.set_exp_param(exp_config_file, "servo_mode", 1)
    config.set_exp_param(exp_config_file, "config_adc_offset_all", 0)

    config.set_exp_param_range(exp_config_file, "adc_offset_c", rc_indices,
            adc_offset_c)

    config.set_exp_param_range(exp_config_file, "sq2_bias", rc_indices,
            adc_offset_c)

    config.set_exp_param(exp_config_file, "sq1_bias", 0)
    config.set_exp_param(exp_config_file, "sq1_bias_off", 0)

    # SA lock slope is determined by sign of sq2servo gain

    sa_slope = -idl_compat.sign(config.get_exp_param(exp_config_file,
        "sq2servo_gain")[rc - 1])

    # if we want to find the SSA bias again
    if (ramp_sa_bias):
        status2 = util.mce_make_config(params_file=exp_config_file,
                filename=config_mce_file, run_now=1)

        if (status2 != 0):
            print "An error has occured just before running the ramp_sa script"
            return 2

        acquire.series_array(file_name, rc, quiet, directory)

        sa_dict = reduce.series_array(directory, file_name, rc, numrows, acq_id,
                ramp_bias, quiet, poster, slope)
        
        config.set_exp_config_range(exp_config_file, "sa_bias", rc_indices,
                sa_dict["final_sa_bias_ch_by_ch"])

        sa_offset_MCE2 = floor(final_sa_bias_ch_by_ch *
                config.get_exp_param(exp_config_file, "sa_offset_bias_ratio"))

        config.set_exp_config_range(exp_config_file, "sa_offset", rc_indices,
                sa_offset_MCE2)

        config.set_exp_config(exp_config_file, "config_adc_offset_all", 0)
        config.set_exp_config_range(exp_config_file, "adc_offset_c", rc_indices,
            sa_dict["SA_target"])

        column_adc_offset[rc_indices] = sa_dict["SA_target"]
    else:
        # Instead of ramping the SA bias, just use the default values, and ramp
        # the SA fb to confirm that the v-phi's look good.

        config.set_exp_config(exp_config_file, "sa_bias", rc_indices,
                def_sa_bias[rc_indices])

        sa_offset_MCE2 = floor(def_sa_bias *
                config.get_exp_param(exp_config_file, "sa_offset_bias_ratio"))

        config.set_exp_config_range(exp_config_file, "sa_offset", rc_indices,
                sa_offset_MCE2[rc_indices])

        status3 = util.mce_make_config(params_file=exp_config_file,
                filename=config_mce_file, run_now=1)

        if (status3 != 0):
            print "An error has occured just before running the ramp_sa script"
            return 3

        sa_dict = report.ssa_file_name(rc=rc, slope=sa_slope, numrows=numrows,
                acq_id=acq_id, quiet=quiet)

        config.set_exp_config(exp_config_file, "config_adc_offset_all", 0)
        config.set_exp_config_range(exp_config_file, "adc_offset_c", rc_indices,
                sa_dict["SA_target"])

        column_adc_offset[rc_indices] = sa_dict["SA_target"]

    status5 = util.mce_make_config(params_file=exp_config_file,
            filename=config_mce_file, run_now=1)

    if (status5 != 0):
        print "An error has occurred after running the ramp_sa script"
        return 5

# step 3: SQ2 servo block

    # Sets the initial SA fb (found in the previous step or set to mid-range)
    # for the SQ2 servo

    SA_feedback_file.fill(32000)
    SA_feedback_file[rc_indices] = sa_dict["SA_fb_init"]

    f = open(todays_folder + "safb.init")
    for i in range(32):
        f.write("%10i" % (SA_feedback_file[i]))
    f.close()

    # Set data mode, servo mode, turn off sq1 bias, set default sq2 bias
    config.set_exp_param(exp_config_file, "data_mode", 0)
    config.set_exp_param(exp_config_file, "servo_mode", 1)
    config.set_exp_param(exp_config_file, "sq1_bias", 0)
    config.set_exp_param(exp_config_file, "sq1_bias_off", 0)
    config.set_exp_param_range(exp_config_file, "sq2_bias", rc_indices,
            sq2_bias[rc_indices])

    status6 = util.mce_make_config(params_file=exp_config_file,
            filename=config_mce_file, run_now=1)

    if (status6 != 0):
        print "An error has occurred before running the sq2 servo script"
        return 6

    sq2_file_name = util.filename(rc=rc, directory=file_folder)

    # locking slope should be consistent with servo gains.
    sq2slope = -idl_compat.sign(config.get_exp_param(exp_config_file,
        "sq2servo_gain")[rc - 1]) / \
                idl_compat.sign(config.get_exp_param(exp_config_file,
                    "sq1servo_gain")[rc - 1])

    # We may want to do sq2 servos at a series of sq2 biases.

    if (config.get_exp_param(exp_config_file, "sq2_servo_bias_ramp") != 0):
        sq2servo_plot(sq2_file_name, sq2bias=SQ2_bias, rc=rc, slope=sq2slope,
                lockamp=1,acq_id=acq_id,no_analysis=1)

        print "Exiting after sq2servo with bias ramp!"
        return 98
    else:
        sq2_dict = sq2servo_plot(sq2_file_name, sq2bias=SQ2_bias, rc=rc,
                slope=sq2slope, locamp=1, acq_id=acq_id, quiet=quiet)

    config.set_exp_param_range(exp_config_file, "sa_fb", rc_indices,
            sq2_dict["sq2_target"])
    config.set_exp_param(exp_config_file, "sq1_bias", sq1_bias)
    config.set_exp_param(exp_config_file, "sq1_bias_off", sq1_bias_off)

    status8 = util.mce_make_config(params_file=exp_config_file,
            filename=config_mce_file, run_now=1)

    if (status8 != 0):
        print "An error has occurred after running the sq2 servo script"
        return 8

    return 0

def step4():
   
    sq2_feedback = array([8], dtype="int64")
    sq2_feedback.fill(8200) # JPF 090804 (with BAC)
    initial_sq2_fb = 8200

    config.set_exp_param(exp_config_file, "data_mode", 0)
    config.set_exp_param(exp_config_file, "num_rows", numrows)
    config.set_exp_param(exp_config_file, "num_rows_reported", numrows)
    config.set_exp_param(exp_config_file, "servo_mode", 1)
    config.set_exp_param(exp_config_file, "servo_p", 0)
    config.set_exp_param(exp_config_file, "servo_i", 0)
    config.set_exp_param(exp_config_file, "servo_d", 0)

    status9 = util.mce_make_config(params_file=exp_config_file,
            filename=config_mce_file, run_now=1)

    if (status9 != 0):
        print "An error has occurred before running the sq1 servo script"
        return 9

    # Sets the initial SQ2 fb (found in the previous step or set to mid-range)
    # for the SQ1 servo

    sq2_feedback_file[rc_indices] = sq2_feedback

    f = open(todays_folder + "sq2fb.init")
    for i in range(32):
        f.write("%10i" % (sq2_feedback_file[i]))
    f.close()

    sq1_base_name = util.filename(rc=rc, directory=file_folder)

    # Here we either
    # a) servo each row of each column
    # b) servo a selected row from each column
    #
    # The first option is always used in fast_sq2 mode, but may
    # also be invoked with per-column sq2 during initial runs to
    # determine the representative row in each column.

    # Locking slope should be consistent with servo gains.
    sq1slope = -idl_compat.sign(config.get_exp_param(exp_config_file,
        "sq1servo_gain")[rc - 1]) / \
                idl_compat.sign(config.get_exp_param(exp_config_file,
                    "sq1servo_gain")[(rc - 1) * 8 : rc * 8])

    config_fast_sq2 = config.get_exp_param(exp_config_file, "config_fast_sq2")
    if (config_fast_sq2 or config.get_exp_param(exp_config_file,
        "sq1_servo_all_rows")):
        # This block uses either sq1servo or sq1servo_all to get
        # the full block of ramps for all rows.

        sq2_feedback_full_array = empty([numrows,8], dtype="int64")

        if (config_fast_sq2):
            # Super-servo, outpus a separate .bias file for each
            # row but produces only one data/.run file

            if (quiet == 0):
                print "Using biasing address card (bac) to sq1servo each row separately"

            sq1_dict = sq1servo_plot(sq1_base_name, sq1bias=sq1_bias, rc=rc,
                    numrows=numrows, slope=sq1slope, super_servo=1,
                    acq_id=acq_id)

            runfile = sq1_base_name + "_sq1servo.run"

        for sq1servorow in range(numrows):
            sq1_file_name = sq1_base_name + "_row" + sq1servorow

            if (not config_fast_sq2):
                # We have to call sq1servo with row.init set
                f = todays_folder + "row.init"
                for i in range(32):
                    f.write("%i10" % sq1servorow)
                f.close()

                sq1_dict = sq1servo_plot(sq1_file_name, sq1bias=sq1_bias, rc=rc,
                        numrows=numrows, slope=sq1slope)
            else:
                # Fast sq2 equivalent: use data produced by the super servo!
                bias_file = sq1_base_name + \
                        "_sq1servo.r%02i.bias" % (sq1servorow)

                sq1_dict = sq1servo_plot(sq1_file_name, sq1bias=sq1_bias, rc=rc,
                        numrows=numrows, slope=sq1slope,
                        use_bias_file=bias_file, use_run_file=runfile)

            sq2_feedback_full_array[sq1servorow, ...] = sq1_dict["sq1_target"]

        # Save all sq2fb points
        for j in rc_indices.size:
            sq2_rows = 41
            c_ofs = rc_indices[j] * sq2_rows
            config.set_exp_param(exp_config_file, "sq2_fb_set", arange(c_ofs,
                c_ofs + numrows), sq2_feedback_full_array[..., j])

        # For single rowing; use the selected rows from sq2_param:
        sq2_rows = config.get_exp_param(exp_config_file, "sq2_rows")
        for j in range(8):
            sq1_target[j] = sq2_feedback_full_array(sq2_rows[rc_indices[j]], j)

    else:
        # This block uses original sq1servo to
        # lock on a specific row for each column

        # Rewrite the row.init file
        sq2_rows = config.get_exp_param(exp_config_file, "sq2_rows")
        f = open(todays_folder + "row.init")
        for j in range(32):
            f.write("%10i", sq2_rows[j])
        f.close()

        sq1_file_name = sq1_base_name

        sq1_dict = sq1servo_plot(sq1_file_name, sq1bias = sq1_bias, rc = rc,
                numrows=numrows, slope=sq1slope, acq_id=acq_id)

    # done.

    # Single row approach -- these will be ignored in the multi-variable case!

    config.set_exp_param_range(exp_config_file, "sq2_fb", rc_indices,
            sq1_target)

    status11 = util.mce_make_config(params_file=exp_config_file,
            filename=config_mce_file, run_now=1)

    if (status11 != 0):
        print "An error has occurred after running the sq1servo script"
        return 11

    f = open(todays_folder + "sq2fb.init")
    for i in range(32):
        f.write(sq1_target[i % 8])
    f.close()

def sq1_ramp_check(rcs, exp_config_file):
    for rc in rcs:
        rc_indices = (rc - 1) * 8 + arange(8)

        print "ADC offsets of rc " + rc

        config.set_exp_param(exp_config_file, "data_mode", 0)
        config.set_exp_param(exp_config_file, "servo_mode", 1)
        config.set_exp_param(exp_config_file, "servo_p", 0)
        config.set_exp_param(exp_config_file, "servo_i", 0)
        config.set_exp_param(exp_config_file, "servo_d", 0)
        config.set_exp_param(exp_config_file, "config_adc_offset_all", 0)
        config.set_exp_param(exp_config_file, "sq1_bias", sq1_bias)
        config.set_exp_param(exp_config_file, "sq1_bias_off", sq1_bias_off)

        status12 = util.mce_make_config(params_file=exp_config_file,
                filename=config_mce_file, run_now=1)

        if (status12 != 0):
            print "An error occurred before running the sq1ramp check"
            return 12

        rsq1_file_name = 3

def auto_setup(column, row, text, rc=None, check_bias=False, short=False,
        numrows=33, acq_id=0, ramp_sa_bias=False, quiet=False,
        interactive=False, slope=1, note=None, data_root=None):
    """
Run a complete auto setup.

This metafunction runs, in turn, each of acquisition, tuning, and reporting
functions to perform an entire auto setup procedure, exactly like the old
IDL auto_setup_squids."""

    tuning = util.tuningData(data_root=data_root)

    # set_directory creates directories and files where to store the tuning data
    # and plots

    # XXX set_directory does not respect data_root
    if (not short):
        tuning.run("set_directory")

    config_mce_file = todays_directory + "config_mce_auto_setup_" + current_data

    file_dir = "%10i" % (tuning.name)

    # logfile
    try:
        logfile = open(todays_directory + c_filename + ".log", "w+")
    except IOError as (errno, strerror):
        print "Unable to create logfile (errno: {0}; {1})\nLogging disabled."\
                .format(errno, strerror)
        logfile = None

    print "auto_setup initialising"
    cont = step1(directory, rc, check_bias, short, numrows, ramp_sa_bias, note)

    if (cont == 0):
        return

    # starts the cycle over the 4 rcs to set all the bias ad fb
    for c in rc:
        rc_indices = 8 * (c - 1) + arange([8])

        if (short):
            column_adc_offset[rc_indices] = \
                    config.get_exp_param(exp_config_file,
                            "adc_offset_c")[rc_indices]

            if (short == 1):
                next_step = 4
            else:
                continue
        else:
            next_step = 2

        print "Processing rc" + c

        if (next_step == 2):
            e = step2and3()
            if (e != 0):
                return e

        if (next_step == 4):
            e = step4()
            if (e != 0):
                return e


    if (config.get_exp_param(exp_config_file, "stop_after_sq1_servo") == 1):
        print "stop_after_sq1servo is set, stopping."
        return 98

    # sq1 ramp check
    sq1_ramp_check()

