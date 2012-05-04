#!/bin/bash

# The following environmental variables, if they are set, affect this
# script:
#
# o  MAS_ROOT:    to use something other than the default, installed
#                 MCE script, point this to your checked out copy, e.g.:
#
#                 export MAS_ROOT="/home/mhasse/mce_script/trunk/"
#
# o  MAS_MCE_DEV: ignored if MAS doesn't have multicard capability.  If
#                 multicard capability *is* enabled, set this to the
#                 fibre card number you want to use, e.g.:
#
#                 export MAS_MCE_DEV=1
#
# o  MAS_CONFIG:  to use a non-standard MCE config directory, point this
#                 variable to it, e.g.:
#
#                 export MAS_CONFIG="/data/mce_test_config/"
#
# Default values are used for variables which aren't set.  All other
# MAS variables will be overwritten by this script.  It also updates
# PATH and PYTHONPATH appropriately.
#
# To get this script to do anything useful, you have to source it after
# possibly setting the above variables, e.g:
#
#       export MAS_ROOT="/home/mhasse/mce_script/trunk/"
#       source mas_env.bash

#unset volitile variables
unset MAS_BIN
unset MAS_TEMP
unset MAS_DATA_ROOT
unset MAS_DATA

unset MAS_IDL
unset MAS_PYTHON
unset MAS_TEMPLATE
unset MAS_TEST_SUITE

#now reset the environment
if [ ! -x ${MAS_VAR:=/usr/mce/bin/mas_var} ]; then
  echo "Cannot find mas_var.  Set MAS_VAR to the full path to the mas_var binary." >&2
else
  eval $(${MAS_VAR} -s)
fi
