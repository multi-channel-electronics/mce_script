#!/bin/bash

# To run mce_script from your own checked-out source tree, point
# the MAS_ROOT variable to your checked out copy and then call
# mas_set_environment.  e.g.:
#
#     export MAS_ROOT="/home/mhasse/mce_script/trunk/"
#     mas_set_environment
#
# If your .bashrc sources mas_env.bash automatically, with a different
# MAS_ROOT, you probably need to set the $PATH variable by hand as it
# will still preferentially run things from the old directories.

# To run mce_script with a non-standard MAS install, point MAS_CONFIG to
# the associated mas_config program, and run mas_set_environment to update
# everything
if [ -z "$MAS_CONFIG" ]; then
  export MAS_CONFIG=/usr/mce/bin/mas_config
fi

# This function is responsible for ensuring the MAS environment is sane;
# It accepts one optional argument, a logical fibre card number (which is
# ignored unless running multicard MAS).
function mas_set_environment {
  local card=$1

  # sanity check
  if [ -z "$MAS_CONFIG" ]; then
    echo "mas_set_environment: \$MAS_CONFIG is not set"
    false
    return
  elif [ ! -x "$MAS_CONFIG" ]; then
    echo "mas_set_environment: \$MAS_CONFIG is not executable"
    false
    return
  fi

  # if the user passed in a card number, update it, otherwise, if no card
  # number has been specified, use the current default
  if [ -z "$card" ]; then
    MAS_CARD=$($MAS_CONFIG --fibre-card)
  else
    MAS_CARD=$($MAS_CONFIG -n $card --fibre-card)
  fi
  export MAS_CARD

  # if the user has set MAS_ROOT, honour it
  if [ -z "$MAS_ROOT" ]; then
    export MAS_ROOT=/usr/mce/mce_script
  fi

  # Now update the rest of the environment; mas_config will honour previously
  # exported environment
  export MAS_PREFIX=$($MAS_CONFIG --prefix)

  local path_base=$($MAS_CONFIG --path-base)
  local pythonpath_base=$($MAS_CONFIG --pythonpath-base)

  export MAS_BIN=$($MAS_CONFIG --bin-dir)
  export MAS_TEMP=$($MAS_CONFIG --temp-dir)
  export MAS_DATA_ROOT=$($MAS_CONFIG --data-root)
  export MAS_DATA=$($MAS_CONFIG --data-dir)

  export MAS_TEMPLATE=$($MAS_CONFIG --template-dir)
  export MAS_SCRIPT=$($MAS_CONFIG --script-dir)
  export MAS_TEST_SUITE=$($MAS_CONFIG --test-suite)
  export MAS_IDL=$($MAS_CONFIG --idl-dir)
  export MAS_PYTHON=$($MAS_CONFIG --python-dir)

  export PATH=$($MAS_CONFIG --path=$path_base)
  export PYTHONPATH=$($MAS_CONFIG --pythonpath=$pythonpath-base)
  true
}
export -f mas_set_environment

# set up the environment for the default fibre card
mas_set_environment
