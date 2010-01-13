import acquire
import reduce
import report
import util
import config

import os
import subprocess
import time

def auto_setup(column, row, text, note, rc=None, check_bias=False, short=False,
    numrows=33, acq_id=0, ramp_sa_bias=False, quiet=False, interactive=False,
    slope=1):
  """
Run a complete auto setup.

This metafunction runs, in turn, each of acquisition, tuning, and reporting
functions to perform an entire auto setup procedure, exactly like the old
IDL auto_setup_squids."""

  directory = "/data/cryo"

  print "auto_setup initialising"

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

  acquire.initialise(rc, check_bias, logfile)
  acquire.series_array(file_name, rc, quiet, directory)
