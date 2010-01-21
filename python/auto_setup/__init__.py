"""MCE auto setup script.

This programme doesn't work!
"""

# This is a semitranslation of the IDL auto_setup_squids program.  The
# intent is to separate that program into three broad parts:
#
#  1) Data acquisition  (acquire subpackage)
#  2) Data Reduction and Tuning Calculations  (reduce subpackage)
#  3) Reporting (ie. Plots &c.)  (report subpackage)
#
# Because necessary data is stored after each of the above steps, it is 
# possible to run only part of the procedure, if the location of the output
# of previous step(s) is provided.

# -- Handy ruler ------------------------------------------------------|

import idl_compat
import util
import config

import acquire
import reduce
import report

from main import auto_setup
import series_array, sq2_servo, sq1_servo
