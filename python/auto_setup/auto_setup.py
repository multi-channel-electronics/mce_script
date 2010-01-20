import acquire
import reduce
import report
import util
import config

import os
import subprocess
import time


def step1 (directory, rc, check_bias, short, numrows, ramp_sa_bias, note):
  # set_directory creates directories and files where to store the tuning data
  # and plots
  if (not short):
    subprocess.call("set_directory")

  current_data = util.current_data_name();
  todays_directory = directory + current_data + "/"
  config_mce_file = todays_directory + "config_mce_auto_setup_" + current_data

  exp_config_file = todays_directory + "experiment.cfg"

  the_time = time.time();
  file_dir = "%10i" % (the_time)

  # logfile
  try:
    logfile = open(todays_directory + c_filename + ".log", "w+")
  except IOError as (errno, strerror):
    print "Unable to create logfile (errno: {0}; {1})\nLogging disabled."\
        .format(errno, strerror)
    logfile = None

  # directory containing data files
  os.mkdir(todays_directory + file_dir)

  # directory containing plots
  os.mkdir(todays_directory + "analysis/" + file_dir)

  c_filename = file_dir + "/" + file_dir

  if (rc == None):
    print "  No read-out cards specified; setting all available RCs."
    rc = config.rc_list(exp_config_file);

  # check whether the SSA and SQ2 biases have already been set
  on_bias = False
  if (check_bias):
    for c in rc:
      exit = subprocess.Popen(["check_zero", "rc" + c, "sa_bias"], stdout=log,
          stderr=log).wait()

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
  SA_feedback_file = numpy.empty([32], dtype="int64")
  SA_feedback_file.fill(32000)

  SQ2_feedback_file = numpy.empty([32], dtype="int64")
  SQ2_feedback_file.fill(8200)

  column_adc_offset = numpy.empty([32], dtype="int64")

  if (config.get_exp_param(exp_config_file, "tes_bias_do_reconfig") != 0):
    # detector bias
    print "driving TES normal, then to idle value."

    # setting detectors bias by first driving them normal and then
    # to the transition.

    # XXX check loop limits
    cfg_tes_bias_norm = config.get_exp_param(exp_config_file, "tes_bias_normal")
    for i in cfg_tes_bias_norm.size():
      util.cmd("wra tes bias {0} {1}".format(i, cfg_tes_bias_norm[i]))

    time.sleep(config.get_exp_param(exp_config_file, "tes_bias_normal_time"))

    cfg_tes_bias_idle = config.get_exp_param(exp_config_file, "tes_bias_idle")
    config.set_exp_param(exp_config_file, "tes_bias", cfg_tes_bias_idle);
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
  status1 = mce_make_config(params_file=exp_config_file,
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
  f.write("\n<SQ_tuning_dir> " + the_time + "\n</SQUID>\n")
  f.close()

  subprocess.call(["rm", "-f", directory + "/last_squid_tune"])
  subprocess.call(["ln", "-s", todays_folder + c_filename + ".sqtune",
    directory + "/last_squid_tune"])

  return 1


def step2(rc, file_folder):
  ssa_file_name = util.filename(rc=rc, directory=file_folder)


def auto_setup(column, row, text, rc=None, check_bias=False, short=False,
    numrows=33, acq_id=0, ramp_sa_bias=False, quiet=False, interactive=False,
    slope=1, note=None):
  """
Run a complete auto setup.

This metafunction runs, in turn, each of acquisition, tuning, and reporting
functions to perform an entire auto setup procedure, exactly like the old
IDL auto_setup_squids."""

  directory = "/data/cryo"

  print "auto_setup initialising"
  cont = step1(directory, rc, check_bias, short, numrows, ramp_sa_bias, note)

  if (cont == 0):
    return

  # starts the cycle over the 4 rcs to set all the bias ad fb
  for c in rc:
    rc_indices = 8 * (c - 1) + arange([8])

    if (short):
      column_adc_offset[rc_indices] = config.get_exp_param(exp_config_file,
          "adc_offset_c")[rc_indices]

      if (short == 1):
        next_step = 4
      else:
        next_step = 5
    else:
      next_step = 2

    print "Processing rc" + c

    if (next_step == 2):
      next_step = step2()
    
    if (next_step == 3):
      next_step = step3()

    if (next_step == 4):
      next_step = step4()

    if (next_step == 5):
      next_step = step5()

  acquire.series_array(file_name, rc, quiet, directory)
