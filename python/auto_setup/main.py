# vi: ts=4:sw=4:et
import util
import series_array
import sq2_servo
import sq1_servo

import os
import subprocess
import time
import shutil
from numpy import *


def initialise (tuning, rcs, check_bias, short, numrows, ramp_sa_bias, note):
    c_filename = os.path.join(tuning.base_dir, tuning.base_dir)

    # check whether the SSA and SQ2 biases have already been set
    on_bias = False
    if (check_bias):
        for c in rcs:
            exit_status = tuning.run(["check_zero", "rc%i" % (c), "sa_bias"])
            if (exit > 8):
                print "check_zero failed with code", exit_status
            on_bias += exit_status

    on_sq2bias = tuning.run(["check_zero", "sq2", "bias"])


    # load camera defaults from experiment config file
    if (numrows == None):
        numrows= tuning.get_exp_param("default_num_rows")

    # set this to 1 to sweep the tes bias and look at squid v-phi response.
    ramp_sq1_bias_run=tuning.get_exp_param("sq1_ramp_tes_bias")

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
    tuning.set_exp_param("sq1_bias", zeros([len(sq1_bias)]))
    tuning.set_exp_param("sq1_bias_off", zeros([len(sq1_bias_off)]))

    # Save experiment params, make config script, run it.
    tuning.write_config()
  
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
    f.write(tuning.current_data)
    f.write("\n<SQ_tuning_dir> " + tuning.name + "\n</SQUID>\n")
    f.close()

    lst = os.path.join(tuning.data_root, "last_squid_tune")
    try:
      os.remove(lst)
    except OSError:
      pass # last_squid_tune didn't exist

    os.symlink(tuning.sqtune_file, lst)

    return {"ramp_sa_bias": ramp_sa_bias, "sq1_bias": sq1_bias,
            "sq1_bias_off": sq1_bias_off, "sq2_bias": sq2_bias}


def sa_and_sq2(tuning, rc, rc_indices, tune_data, sa_feedback_file):
    def_sa_bias = tuning.get_exp_param("default_sa_bias")

    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.set_exp_param("config_adc_offset_all", 0)

    tuning.set_exp_param_range("adc_offset_c", rc_indices,
            zeros(len(rc_indices), dtype="int"))
    tuning.set_exp_param_range("sq2_bias", rc_indices, zeros(len(rc_indices),
        dtype="int"))

    tuning.set_exp_param("sq1_bias", zeros([len(tune_data["sq1_bias"])]))
    tuning.set_exp_param("sq1_bias_off",
        zeros([len(tune_data["sq1_bias_off"])]))

    # SA lock slope is determined by sign of sq2servo gain

    column_adc_offset = empty([32], dtype="int64")

    if (not tune_data["ramp_sa_bias"]):
        # Instead of ramping the SA bias, just use the default values, and ramp
        # the SA fb to confirm that the v-phi's look good.
        tuning.set_exp_param_range("sa_bias", rc_indices,
                def_sa_bias[rc_indices])

        sa_offset_MCE2 = floor(def_sa_bias *
                tuning.get_exp_param("sa_offset_bias_ratio"))

        tuning.set_exp_param_range("sa_offset", rc_indices,
                sa_offset_MCE2[rc_indices].astype("int"))

    tuning.write_config()

    sa_dict = series_array.go(tuning, rc, do_bias=tune_data["ramp_sa_bias"])

    tuning.set_exp_param("config_adc_offset_all", 0)
    tuning.set_exp_param_range("adc_offset_c", rc_indices,
            sa_dict["sa_target"])

    column_adc_offset[rc_indices] = sa_dict["sa_target"]

    #tuning.write_config()

# step 3: SQ2 servo block

    # Sets the initial SA fb (found in the previous step or set to mid-range)
    # for the SQ2 servo

    sa_feedback_file[rc_indices] = sa_dict["sa_fb_init"]
    f = open(os.path.join(tuning.base_dir, "safb.init"), "w")
    for x in sa_feedback_file:
        f.write("%i\n" % x)
    f.close()

    # Set data mode, servo mode, turn off sq1 bias, set default sq2 bias
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.set_exp_param("sq1_bias", zeros([len(tune_data["sq1_bias"])]))
    tuning.set_exp_param("sq1_bias_off",
        zeros([len(tune_data["sq1_bias_off"])]))
    tuning.set_exp_param_range("sq2_bias", rc_indices,
            tune_data["sq2_bias"][rc_indices])

    tuning.write_config()

    sq2_data = sq2_servo.go(tuning, rc, bias=tune_data["ramp_sa_bias"])

    if (tuning.get_exp_param("sq2_servo_bias_ramp") != 0):
        print "Exiting after sq2servo with bias ramp!"
        return {"status": 98}

    tuning.set_exp_param_range("sa_fb", rc_indices, sq2_data["sq2_target"])
    tuning.set_exp_param("sq1_bias", tune_data["sq1_bias"])
    tuning.set_exp_param("sq1_bias_off", tune_data["sq1_bias_off"])

    tuning.write_config()

    return {"status": 0, "column_adc_offset": column_adc_offset}

def do_sq1_servo(tuning, rc, rc_indices, numrows, sq2_feedback_file):
   
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

    tuning.write_config()

    # Sets the initial SQ2 fb (found in the previous step or set to mid-range)
    # for the SQ1 servo

    sq2_feedback_file[rc_indices] = sq2_feedback

    sq1_base_name, acq_id = tuning.filename(rc=rc)

    f = open(os.path.join(tuning.base_dir, "sq2fb.init"), "w")
    for x in sq2_feedback_file:
        f.write("%i\n" % x)
    f.close()

    sq1_data = sq1_servo.go(tuning, rc)

    # XXX need to save big array from super servo here.

    # Save all sq2fb points
    #for j in rc_indices.size:
    #    sq2_rows = 41
    #    c_ofs = rc_indices[j] * sq2_rows
    #    tuning.set_exp_param("sq2_fb_set", arange(c_ofs,
    #        c_ofs + numrows), sq2_feedback_full_array[..., j])

    tuning.set_exp_param_range("sq2_fb", rc_indices, sq1_data["sq1_target"])

    tuning.write_config()

    return 0

def sq1_ramp_check(tuning, rcs, numrows, tune_data):
    new_adc_arr = [ "" ] * 32
    squid_p2p_arr = [ "" ] * 32
    squid_lockrange_arr = [ "" ] * 32
    squid_lockslopedn_arr = [ "" ] * 32
    squid_lockslopeup_arr = [ "" ] * 32
    squid_multilock_arr = [ "" ] * 32
    squid_off_rec_arr = [ "" ] * 32

    for rc in rcs:
        rc_indices = (rc - 1) * 8 + arange(8)

        print "ADC offsets of rc", rc

        tuning.set_exp_param("data_mode", 0)
        tuning.set_exp_param("servo_mode", 1)
        tuning.set_exp_param("servo_p", 0)
        tuning.set_exp_param("servo_i", 0)
        tuning.set_exp_param("servo_d", 0)
        tuning.set_exp_param("config_adc_offset_all", 0)
        tuning.set_exp_param("sq1_bias", tune_data["sq1_bias"])
        tuning.set_exp_param("sq1_bias_off", tune_data["sq1_bias_off"])

        tuning.write_config()

        rsq1_file_name, acq_id = tuning.filename(rc=rc, action="sq1ramp")

        rsq1_data = ramp_sq1_fb_plot(tuning, rc=rc, numrows=numrows,
                acq_id=acq_id)

        if (rc == rcs[0]):
            all_adc_offsets = empty([32, numrows], dtype="float64")
            all_squid_p2p = empty([32, numrows], dtype="float64")
            all_squid_lockrange = empty([32, numrows], dtype="float64")
            all_squid_lockslope = empty([32, numrows, 2], dtype="float64")
            all_squid_multilock = empty([32, numrows], dtype="float64")

        samp_num = tuning.get_exp_param("default_sample_num")
        for j in range(8):
            all_adc_offsets[(rc - 1) * 8 + j, ...] = \
                    (rsq1_data["new_adc_offset"][j, ...] + 
                            column_adc_offset[j + 8 * (rc - 1)]) / samp_num

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

        tuning.write_config()

        # load masks for labeling the ramp plots
        mask_list = ["connection", "other"]
        make_files = [ os.environ["MAS_TEMPLATE"] + os.path.join("dead_lists",
            tuning.get_exp_param("array_id"), "dead_" + m + ".cfg") for m in
            mask_list ]
        extra_lables = util.mask_labels(mask_files, mask_list, rc)
        rsq1c_file_name, acq_id = tuning.filename(rc=rc, action="sq1rampc")

        rsq1_data = ramp_sq1_fb_plot(tuning, rsq1c_file_name, rc=rc,
                numrows=numrows, acq_id=acq_id, extra_labels=extra_labels)

        for j in range(8):
            all_squid_p2p[(rc - 1) * 8 + j, ...] = \
                    rsq1_data["squid_p2p"][j, ...]
            all_squid_lockrange[(rc - 1) * 8 + j, ...] = \
                    rsq1_data["squid_lockrange"][j, ...]
            all_squid_lockslope[(rc - 1) * 8 + j, ..., ...] = \
                    rsq1_data["squid_lockslope"][j, ..., ...]
            all_squid_multilock[(rc - 1) * 8 + j, ...] = \
                    rsq1_data["squid_multilock"][j, ...]

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
            tuning.write_config()

            rtb_file_name, acq_id = tuning.filename(rc=rc, action="sq1rampb")

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

    tuning.write_config()

    # Permit row override, or else take it from config
    if (row == None):
        row = tuning.get_exp_param("locktest_plot_row")
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

    # Compile dead detector mask
    print "Assembling dead detector mask."
    mask = mask_dead(tuning, mask,
            filespec=os.path.join(os.eviron["MAS_TEMPLATE"], dead_lists,
                tuning.get_exp_param("array_id"), "dead_*.cfg"))
    tuning.set_exp_param("dead_detectors", mask)

    # Run config one last time in *case* frametest plot changes to data
    # mode 4, and to set dead detector mask
    tuning.write_config()




def auto_setup(rcs=None, check_bias=False, short=False, row=None,
        column=None, numrows=33, acq_id=0, ramp_sa_bias=False, slope=1,
        note=None, data_root=None, debug=False):
    """
Run a complete auto setup.

This metafunction runs, in turn, each of acquisition, tuning, and reporting
functions to perform an entire auto setup procedure, exactly like the old
IDL auto_setup_squids."""

    tuning = util.tuningData(data_root=data_root, debug=debug)

    # set_directory creates directories and files where to store the tuning data
    # and plots.
    if (not short):
        tuning.run(["set_directory", tuning.data_root], no_log=True)


    # Create data and analysis directories
    tuning.make_dirs()

    # set rc list, if necessary
    if (rcs == None):
        print "  Tuning all available RCs."
        rcs = tuning.rc_list()

    # initialse the auto setup
    tune_data = initialise(tuning, rcs, check_bias, short, numrows,
            ramp_sa_bias, note)

    if (tune_data == None):
        return 1

    # TODO - *bias.init inputs should come from experiment.cfg
    sa_feedback_file = empty([32], dtype="int64")
    sa_feedback_file.fill(32000)

    sq2_feedback_file = empty([32], dtype="int64")
    sq2_feedback_file.fill(8200)

    if (short <= 1):
        # starts the cycle over the 4 rcs to set all the bias ad fb
        for c in rcs:
            print "Processing rc%i" % c

            rc_indices = 8 * (c - 1) + arange(8)

            if (short):
                column_adc_offset = empty([32], dtype="int64")
                column_adc_offset[rc_indices] = \
                        tuning.get_exp_param("adc_offset_c")[rc_indices]
            else:
                s2_dict = sa_and_sq2(tuning, c, rc_indices, tune_data,
                        sa_feedback_file)
                if (s2_dict["status"] != 0):
                    return s2_dict["status"]
                column_adc_offset = s2_dict["column_adc_offset"]

            e = do_sq1_servo(tuning, c, rc_indices, numrows, sq2_feedback_file)
            if (e != 0):
                return e


    if (tuning.get_exp_param("stop_after_sq1_servo") == 1):
        print "stop_after_sq1servo is set, stopping."
        return 98

    # sq1 ramp check
    sq1_ramp_check(tuning, rcs, numrows, tune_data)

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
        f.write(("<Col%i_squid_vphi_p2p> " % j) + squid_p2p_arr[j])
    for j in range(32):
        f.write(("<Col%i_squid_lockrange> " % j) + squid_lockrange[j])
    for j in range(32):
        f.write(("<Col%i_squid_lockslope_down> " % j) +
            squid_lockslopedn_arr[j])
    for j in range(32):
        f.write(("<Col%i_squid_lockslope_up> " % j) + squid_lockslopeup_arr[j])
    for j in range(32):
        f.write(("<Col%i_squid_multilock> " % j) + squid_multilock_arr[j])
    for j in range(32):
        f.write(("<Col%i_squid_off_recommendation> " % j) +
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
    print "Tuning complete.  Time elapsed: %i seconds." % t_elapsed

    return 99
