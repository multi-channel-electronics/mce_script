# vi: ts=4:sw=4:et
import acquire
import reduce
import report
import util

import os
import subprocess
import time
import shutil
from numpy import *


def step1 (tuning, rc, check_bias, short, numrows, ramp_sa_bias, note):
    c_filename = os.path.join(tuning.base_dir, tuning.base_dir)

    if (rc == None):
        print "  No read-out cards specified; setting all available RCs."
        rc = tuning.rc_list()

    # check whether the SSA and SQ2 biases have already been set
    on_bias = False
    if (check_bias):
        for c in rc:
            exit_status = tuning.run(["check_zero", "rc" + c, "sa_bias"])
            if (exit > 8):
                print "check_zero failed with code " + exit_status
            on_bias += exit_status

    on_sq2bias = tuning.run(["check_zero", "sq2", "bias"])


    # reset the mce
    print "mce_reset_clean suppressed!"

    # load camera defaults from experiment config file
    samp_num = tuning.get_exp_param("default_sample_num")
    if (numrows == None):
        numrows= tuning.get_exp_param("default_num_rows")

    # set this to 1 to sweep the tes bias and look at squid v-phi response.
    ramp_sq1_bias_run=tuning.get_exp_param("ramp_tes_bias")

    # experiment.cfg setting may force a ramp_sa_bias.
    if (ramp_sa_bias == None):
        ramp_sa_bias = tuning.get_exp_param("sa_ramp_bias")

    # TODO - *bias.init inputs should come from experiment.cfg
    SA_feedback_file = empty([32], dtype="int64")
    SA_feedback_file.fill(32000)

    SQ2_feedback_file = empty([32], dtype="int64")
    SQ2_feedback_file.fill(8200)

    column_adc_offset = empty([32], dtype="int64")

    if (tuning.get_exp_param("tes_bias_do_reconfig") != 0):
        # detector bias
        print "driving TES normal, then to idle value."

        # setting detectors bias by first driving them normal and then
        # to the transition.
        cfg_tes_bias_norm = tuning.get_exp_param("tes_bias_normal")
        for i in cfg_tes_bias_norm.size():
            util.cmd("wra tes bias {0} {1}".format(i, cfg_tes_bias_norm[i]))

        time.sleep(tuning.get_exp_param("tes_bias_normal_time"))

        cfg_tes_bias_idle = tuning.get_exp_param("tes_bias_idle")
        tuning.set_exp_param("tes_bias", cfg_tes_bias_idle)
        for i in cfg_tes_bias_idle.size():
            util.cmd("wra tes bias {0} {1}".format(i, cfg_tes_bias_idle[i]))

    # load squid biases from config file default parameters

    def_sa_bias = tuning.get_exp_param("default_sa_bias")
    sq2_bias = tuning.get_exp_param("default_sq2_bias")
    sq1_bias = tuning.get_exp_param("default_sq1_bias")
    sq1_bias_off = tuning.get_exp_param("default_sq1_bias_off")

    # Turn flux-jumping off for tuning, though it shouldn't matter
    tuning.set_exp_param("flux_jumping", 0)

    # load default values into biases

    tuning.set_exp_param("sa_bias", def_sa_bias)
    tuning.set_exp_param("sq2_bias", sq2_bias)
    tuning.set_exp_param("sq1_bias", 0)
    tuning.set_exp_param("sq1_bias_off", 0)

    # Save experiment params, make config script, run it.
    status1 = tuning.mce_make_config(True)
  
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
        f = open(tuning.note_file, "w+")
        f.write("#Note entered with SQUID autotuning data acquisition\n")
        f.write(note)
        f.write("\n")
        f.close()

    # initialise the squid tuning results file
    f = open(tuning.sqtune_file, "w")
    f.write("<SQUID>\n<SQ_tuning_completed> 0\n<SQ_tuning_date> ")
    f.write(current_data)
    f.write("\n<SQ_tuning_dir> " + tuning.name + "\n</SQUID>\n")
    f.close()

    tuning.run(["rm", "-f", directory + "/last_squid_tune"])
    tuning.run(["ln", "-s", todays_folder + c_filename + ".sqtune",
        directory + "/last_squid_tune"])

    return 1


def step2and3(tuning, rc, rc_indices, def_sa_bias):
    ssa_file_name = tuning.filename(rc=rc)

    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.set_exp_param("config_adc_offset_all", 0)

    tuning.set_exp_param_range("adc_offset_c", rc_indices, adc_offset_c)
    tuning.set_exp_param_range("sq2_bias", rc_indices, adc_offset_c)

    tuning.set_exp_param("sq1_bias", 0)
    tuning.set_exp_param("sq1_bias_off", 0)

    # SA lock slope is determined by sign of sq2servo gain

    sa_slope = -idl_compat.sign(tuning.get_exp_param("sq2servo_gain")[rc - 1])

    # if we want to find the SSA bias again
    if (ramp_sa_bias):
        status2 = tuning.mce_make_config(True)

        if (status2 != 0):
            print "An error has occurred just before running the ramp_sa script"
            return 2

        acquire.series_array(tuning, rc, directory)

        sa_dict = reduce.series_array(tuning, rc, numrows, acq_id, ramp_bias,
                slope)
        
        tuning.set_exp_config_range("sa_bias", rc_indices,
                sa_dict["final_sa_bias_ch_by_ch"])

        sa_offset_MCE2 = floor(final_sa_bias_ch_by_ch *
                tuning.get_exp_param("sa_offset_bias_ratio"))

        tuning.set_exp_config_range("sa_offset", rc_indices, sa_offset_MCE2)

        tuning.set_exp_config("config_adc_offset_all", 0)
        tuning.set_exp_config_range("adc_offset_c", rc_indices,
                sa_dict["SA_target"])

        column_adc_offset[rc_indices] = sa_dict["SA_target"]
    else:
        # Instead of ramping the SA bias, just use the default values, and ramp
        # the SA fb to confirm that the v-phi's look good.

        tuning.set_exp_param("sa_bias", rc_indices, def_sa_bias[rc_indices])

        sa_offset_MCE2 = floor(def_sa_bias *
                tuning.get_exp_param("sa_offset_bias_ratio"))

        tuning.set_exp_param_range("sa_offset", rc_indices,
                sa_offset_MCE2[rc_indices])

        status3 = tuning.mce_make_config(True)

        if (status3 != 0):
            print "An error has occurred just before running the ramp_sa script"
            return 3

        sa_dict = report.ssa_file_name(rc=rc, slope=sa_slope, numrows=numrows,
                acq_id=acq_id)

        tuning.set_exp_param("config_adc_offset_all", 0)
        tuning.set_exp_param_range("adc_offset_c", rc_indices,
                sa_dict["SA_target"])

        column_adc_offset[rc_indices] = sa_dict["SA_target"]

    status5 = tuning.mce_make_config(True)

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
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.set_exp_param("sq1_bias", 0)
    tuning.set_exp_param("sq1_bias_off", 0)
    tuning.set_exp_param_range("sq2_bias", rc_indices, sq2_bias[rc_indices])

    status6 = tuning.mce_make_config(True)

    if (status6 != 0):
        print "An error has occurred before running the sq2 servo script"
        return 6

    sq2_file_name = tuning.filename(rc=rc)

    # locking slope should be consistent with servo gains.
    sq2slope = -idl_compat.sign(tuning.get_exp_param("sq2servo_gain")[rc - 1]) \
            / idl_compat.sign(tuning.get_exp_param("sq1servo_gain")[rc - 1])

    # We may want to do sq2 servos at a series of sq2 biases.

    if (tuning.get_exp_param("sq2_servo_bias_ramp") != 0):
        sq2servo_plot(tuning, sq2_file_name, sq2bias=SQ2_bias, rc=rc,
                slope=sq2slope, lockamp=1, acq_id=acq_id, no_analysis=1)

        print "Exiting after sq2servo with bias ramp!"
        return 98
    else:
        sq2_dict = sq2servo_plot(tuning, sq2_file_name, sq2bias=SQ2_bias, rc=rc,
                slope=sq2slope, locamp=1, acq_id=acq_id)

    tuning.set_exp_param_range("sa_fb", rc_indices, sq2_dict["sq2_target"])
    tuning.set_exp_param("sq1_bias", sq1_bias)
    tuning.set_exp_param("sq1_bias_off", sq1_bias_off)

    status8 = tuning.mce_make_config(True)

    if (status8 != 0):
        print "An error has occurred after running the sq2 servo script"
        return 8

    return 0

def step4():
   
    sq2_feedback = array([8], dtype="int64")
    sq2_feedback.fill(8200) # JPF 090804 (with BAC)
    initial_sq2_fb = 8200

    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("num_rows", numrows)
    tuning.set_exp_param("num_rows_reported", numrows)
    tuning.set_exp_param("servo_mode", 1)
    tuning.set_exp_param("servo_p", 0)
    tuning.set_exp_param("servo_i", 0)
    tuning.set_exp_param("servo_d", 0)

    status9 = tuning.mce_make_config(True)

    if (status9 != 0):
        print "An error has occurred before running the sq1 servo script"
        return 9

    # Sets the initial SQ2 fb (found in the previous step or set to mid-range)
    # for the SQ1 servo

    sq2_feedback_file[rc_indices] = sq2_feedback

    f = open(tuning.sq2fb_init_file)
    for i in range(32):
        f.write("%10i" % (sq2_feedback_file[i]))
    f.close()

    sq1_base_name = tuning.filename(rc=rc)

    # Here we either
    # a) servo each row of each column
    # b) servo a selected row from each column
    #
    # The first option is always used in fast_sq2 mode, but may
    # also be invoked with per-column sq2 during initial runs to
    # determine the representative row in each column.

    # Locking slope should be consistent with servo gains.
    sq1slope = -idl_compat.sign(tuning.get_exp_param("sq1servo_gain")[rc - 1]) \
            / idl_compat.sign(tuning.get_exp_param("sq1servo_gain")[(rc - 1) \
            * 8 : rc * 8])

    config_fast_sq2 = tuning.get_exp_param("config_fast_sq2")
    if (config_fast_sq2 or tuning.get_exp_param("sq1_servo_all_rows")):
        # This block uses either sq1servo or sq1servo_all to get
        # the full block of ramps for all rows.

        sq2_feedback_full_array = empty([numrows,8], dtype="int64")

        if (config_fast_sq2):
            # Super-servo, outpus a separate .bias file for each
            # row but produces only one data/.run file

            print "Using biasing address card (bac) to sq1servo each row separately"

            sq1_dict = sq1servo_plot(tuning, sq1_base_name, sq1bias=sq1_bias,
                    rc=rc, numrows=numrows, slope=sq1slope, super_servo=1,
                    acq_id=acq_id)

            runfile = sq1_base_name + "_sq1servo.run"

        for sq1servorow in range(numrows):
            sq1_file_name = sq1_base_name + "_row" + sq1servorow

            if (not config_fast_sq2):
                # We have to call sq1servo with row.init set
                f = open(tuning.row_init_file)
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
            tuning.set_exp_param("sq2_fb_set", arange(c_ofs,
                c_ofs + numrows), sq2_feedback_full_array[..., j])

        # For single rowing; use the selected rows from sq2_param:
        sq2_rows = tuning.get_exp_param("sq2_rows")
        for j in range(8):
            sq1_target[j] = sq2_feedback_full_array(sq2_rows[rc_indices[j]], j)

    else:
        # This block uses original sq1servo to
        # lock on a specific row for each column

        # Rewrite the row.init file
        sq2_rows = tuning.get_exp_param("sq2_rows")
        f = open(tuning.row_init_file)
        for j in range(32):
            f.write("%10i", sq2_rows[j])
        f.close()

        sq1_file_name = sq1_base_name

        sq1_dict = sq1servo_plot(sq1_file_name, sq1bias = sq1_bias, rc = rc,
                numrows=numrows, slope=sq1slope, acq_id=acq_id)

    # done.

    # Single row approach -- these will be ignored in the multi-variable case!

    tuning.set_exp_param_range("sq2_fb", rc_indices, sq1_target)

    status11 = tuning.mce_make_config(True)

    if (status11 != 0):
        print "An error has occurred after running the sq1servo script"
        return 11

    f = open(tuning.sq2fb_init_file)
    for i in range(32):
        f.write(sq1_target[i % 8])
    f.close()

    return 0

def sq1_ramp_check(tuning, rcs, numrows):
    new_adc_arr = [ "" ] * 32
    squid_p2p_arr = [ "" ] * 32
    squid_lockrange_arr = [ "" ] * 32
    squid_lockslopedn_arr = [ "" ] * 32
    squid_lockslopeup_arr = [ "" ] * 32
    squid_multilock_arr = [ "" ] * 32
    squid_off_rec_arr = [ "" ] * 32

    for rc in rcs:
        rc_indices = (rc - 1) * 8 + arange(8)

        print "ADC offsets of rc " + rc

        tuning.set_exp_param("data_mode", 0)
        tuning.set_exp_param("servo_mode", 1)
        tuning.set_exp_param("servo_p", 0)
        tuning.set_exp_param("servo_i", 0)
        tuning.set_exp_param("servo_d", 0)
        tuning.set_exp_param("config_adc_offset_all", 0)
        tuning.set_exp_param("sq1_bias", sq1_bias)
        tuning.set_exp_param("sq1_bias_off", sq1_bias_off)

        status12 = tuning.mce_make_config(True)

        if (status12 != 0):
            print "An error occurred before running the sq1ramp check"
            return 12

        rsq1_file_name = tuning.filename(rc=rc, action="sq1ramp", acq_id=acq_id)

        rsq1_dict = ramp_sq1_fb_plot(tuning, rc=rc, numrows=numrows,
                acq_id=acq_id)

        if (rc == rcs[0]):
            all_adc_offsets = empty([32, numrows], dtype="float64")
            all_squid_p2p = empty([32, numrows], dtype="float64")
            all_squid_lockrange = empty([32, numrows], dtype="float64")
            all_squid_lockslope = empty([32, numrows, 2], dtype="float64")
            all_squid_multilock = empty([32, numrows], dtype="float64")

        new_off = rsq1_dict["new_adc_offset"]
        for j in range(8):
            new_off[j, ...] = (rsq1_dict["new_adc_offset"][j, ...] + 
                    column_adc_offset[j + 8 * (rc - 1)]) / samp_num
            all_adc_offsets[(rc - 1) * 8 + j, ...] = new_off[j, ...]

        array_width = tuning.get_exp_param("array_width")
        for j in range(8):
            for i in range(numrows):
                tuning.set_exp_param_range("adc_offset_cr",
                        ((rc - 1) * 8 + j) * array_width + i,
                        all_adc_offsets[(rc - 1) * 8 + j, i])
                new_adc_arr[(rc - 1) * 8 + j] += \
                        " %i6" % (all_adc_offsets[(rc - 1) * 8 + j, i])

        # Turn on adc_offset config for all columns
        tuning.set_exp_param("config_adc_offset_all", 1)

        status14 = tuning.mce_make_config(True)

        if (status14 != 0):
            print "An error has occurred after running the sq1ramp check"
            return 14


        # load masks for labeling the ramp plots
        mask_list = ["connection", "other"]
        make_files = [ os.environ["MAS_TEMPLATE"] + os.path.join("dead_lists",
            tuning.get_exp_param("array_id"), "dead_" + m + ".cfg") for m in
            mask_list ]
        extra_lables = util.mask_labels(mask_files, mask_list, rc)
        rsq1c_file_name = tuning.filename(rc=rc, action="sq1rampc",
                acq_id=acq_id)

        rsq1_dict = ramp_sq1_fb_plot(tuning, rsq1c_file_name, rc=rc,
                numrows=numrows, acq_id=acq_id, extra_labels=extra_labels)

        for j in range(8):
            all_squid_p2p[(rc - 1) * 8 + j, ...] = \
                    rsq1_dict["squid_p2p"][j, ...]
            all_squid_lockrange[(rc - 1) * 8 + j, ...] = \
                    rsq1_dict["squid_lockrange"][j, ...]
            all_squid_lockslope[(rc - 1) * 8 + j, ..., ...] = \
                    rsq1_dict["squid_lockslope"][j, ..., ...]
            all_squid_multilock[(rc - 1) * 8 + j, ...] = \
                    rsq1_dict["squid_multilock"][j, ...]

        locktest_pass_amp = tuning.get_exp_param("locktest_pass_amplitude")
        for j in range(8):
            for i in range(numrows):
                squid_p2p_arr[(rc - 1) * 8 + j] += \
                        " %6i" % (all_squid_p2p[(rc - 1) * 8 + j, i])
                squid_lockrange_arr[(rc - 1) * 8 + j] += \
                        " %6i" % (squid_lockrange[(rc - 1) * 8 + j, i])
                squid_lockslopedn_arr[(rc - 1) * 8 + j] += \
                        " %6i" % (all_squid_lockslope[(rc - 1) * 8 + j, i, 0])
                squid_lockslopeup_arr[(rc - 1) * 8 + j] += \
                        " %6i" % (all_squid_lockslope[(rc - 1) * 8 + j, i, 1])
                squid_multilock_arr[(rc - 1) * 8 + j] += \
                        " %6i" % (all_squid_multilock[(rc - 1) * 8 + j, i])
                squid_multilock_arr[(rc - 1) * 8 + j] += " " + \
                        (" 1" if (squid_lockrange[(rc - 1) * 8 + j, i] < \
                        locktest_pass_amp) else " 0")

        # only do rampc if it's a full tuning
        if (tuning.get_exp_param("ramp_tes_bias") == 1 and not short):
            status16 = tuning.mce_make_config(True)

            if (status16 != 0):
                print "An error occurred before setting the new adc_off after ramp_sq1_bias"
                return 16

            rtb_file_name = tuning.filename(rc=rc, action="sq1rampb",
                    acq_id=acq_id)

            ramp_sq1_bias_plot(rtb_file_name, rc=rc, numrows=numrows,
                    acq_id=acq_id)


def frametest_check(tuning, rcs, numrows, row, column):
    tuning.set_exp_param("data_mode", tuning.get_exp_param("default_data_mode"))
    tuning.set_exp_param("servo_mode", 3)
    tuning.set_exp_param("servo_p", tuning.get_exp_param("default_servo_p"))
    tuning.set_exp_param("servo_i", tuning.get_exp_param("default_servo_i"))
    tuning.set_exp_param("servo_d", tuning.get_exp_param("default_servo_d"))
    tuning.set_exp_param("flux_jumping", \
            tuning.get_exp_param("default_flux_jumping"))

    # turn off dog-housed column biases
    columns_off = tuning.get_exp_param("columns_off")
    bad_columns = [c for c in range(len(columns_off)) if columns_off[c] != 0]
    if (bad_columns[0] != -1):
        tuning.set_exp_param_range("sa_bias", bad_columns,
                zeros(len(bad_columns)))
        tuning.set_exp_param_range("sq2_bias", bad_columns,
                zeros(len(bad_columns)))

    status17 = tuning.mce_make_config(True)

    if (status17 != 0):
        print "An error occurred before taking a sample of data"
        return 17

    # Permit row override, or else take it from config
    if (row == None):
        row = tuning.get_exp_param("locktest_plot_row")
        print "Row = " + row + " is used for frametest_plot by default."

    if (len(rcs) < 4):
        for rc in rcs:
            lock_file_name = tuning.filename(rc=rc, action="lock",
                    acq_id=acq_id)
            frametest_plot(lock_file_name, column=column, row=row, rc=rc,
                    binary=1, acq_id=acq_id)
    else:
        lock_file_name = tuning.filename(rc="s", action="lock", acq_id=acq_id)
        rc = 5
        frametest_plot(lock_file_name, column=column, row=row, rc=rc,
                binary=1, acq_id=acq_id)

    # Compile dead detector mask
    print "Assembling dead detector mask."
    mask = mask_dead(tuning, mask,
            filespec=os.path.join(os.eviron["MAS_TEMPLATE"], dead_lists,
                tuning.get_exp_param("array_id"), "dead_*.cfg"))
    tuning.set_exp_param("dead_detectors", mask)

    # Run config one last time in *case* frametest plot changes to data
    # mode 4, and to set dead detector mask
    tuning.mce_make_config(True)




def auto_setup(rcs=None, check_bias=False, short=False, row=None,
        column=None, numrows=33, acq_id=0, ramp_sa_bias=False, slope=1,
        note=None, data_root=None):
    """
Run a complete auto setup.

This metafunction runs, in turn, each of acquisition, tuning, and reporting
functions to perform an entire auto setup procedure, exactly like the old
IDL auto_setup_squids."""

    tuning = util.tuningData(data_root=data_root)

    # set_directory creates directories and files where to store the tuning data
    # and plots.  XXX set_directory does not respect data_root
    if (not short):
        tuning.run("set_directory")


    # Create data and analysis directories
    tuning.make_dirs()

    print "auto_setup initialising"
    cont = step1(tuning, rcs, check_bias, short, numrows, ramp_sa_bias, note)

    if (cont == 0):
        return

    # starts the cycle over the 4 rcs to set all the bias ad fb
    for c in rcs:
        rc_indices = 8 * (c - 1) + arange([8])

        if (short):
            column_adc_offset[rc_indices] = \
                    tuning.get_exp_param("adc_offset_c")[rc_indices]

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


    if (tuning.get_exp_param("stop_after_sq1_servo") == 1):
        print "stop_after_sq1servo is set, stopping."
        return 98

    # sq1 ramp check
    sq1_ramp_check(tuning, rcs, numrows)

    # frametest check
    frametest_check(tuning, rcs, numrows, row, column)

    shutil.copy2(tuning.config_mce_file, os.path.join(tuning.base_dir,
        tuning.name + "config_mce_auto_setup_" + tuning.current_data))

    f = open(tuning.sqtune_file)
    f.write("<SQUID>")
    f.write("<SQ_tuning_completed> 1")
    f.write("<SQ_tuning_date> " + tuning.current_data)
    f.write("<SQ_tuning_dir> " + tuning.name)
    
    for j in range(32):
        f.write("<Col" + j + "_squid_vphi_p2p> " + squid_p2p_arr[j])
    for j in range(32):
        f.write("<Col" + j + "_squid_lockrange> " + squid_lockrange[j])
    for j in range(32):
        f.write("<Col" + j + "_squid_lockslope_down> " +
                squid_lockslopedn_arr[j])
    for j in range(32):
        f.write("<Col" + j + "_squid_lockslope_up> " + squid_lockslopeup_arr[j])
    for j in range(32):
        f.write("<Col" + j + "_squid_multilock> " + squid_multilock_arr[j])
    for j in range(32):
        f.write("<Col" + j + "_squid_off_recommendation> " +
                squid_off_rec_arr[j])

    f.write("</SQUID>")
    f.close()

    lst = os.path.join(tuning.data_root, "last_squid_tune")
    os.remove(lst)
    os.symlink(tuning.sqtune_file, lst)

    f = open(lst + "_name", "w")
    f.write(tuning.current_data)
    f.write(tuning.name)
    f.close()

    shutil.copy2(tuning.exp_file, tuning.data_dir)

    t_elapsed = time.time() - tuning.the_time
    print "Tuning complete.  Time elapsed: " + t_elapsed + "seconds."

    return 99
