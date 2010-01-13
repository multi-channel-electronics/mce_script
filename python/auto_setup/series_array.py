"""MCE auto setup script.

This programme doesn't work!
"""

# This is a semitranslation of the IDL auto_setup_squids program.  The
# intent is to separate that program into three broad parts:
#
#  1) Data acquisition
#  2) Data Reduction and Tuning Calculations
#  3) Reporting (ie. Plots &c.)
#
# Because necessary data is stored after each of the above steps, it is 
# possible to run only part of the procedure, if the location of the output
# of previous step(s) is provided.

# -- Handy ruler ------------------------------------------------------|

import util
import acquire

def series_array(file_name, rc, directory = "/data/cryo", numrows = 33,
    acq_id = 0, ramp_bias = 0, quiet = 0, interactive = 0, poster = 0,
    slope = 1):
  "series array"

  acquire.sa_acquire(file_name, rc, numrows, acq_id, ramp_bias, quiet,
      interactive, poster, slope)

  current_data = util.current_data_name(directory)

  datadir = "/data/cryo" + current_data + "/"

  reduce.series_array(datadir, file_name, rc, numrows, acq_id, ramp_bias,
      quiet, interactive, poster, slope)
