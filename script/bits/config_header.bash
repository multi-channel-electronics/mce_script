#START config_header.bash

#initialise environment
if [ ! -x ${MAS_VAR:=/usr/mce/bin/mas_var} ]; then
  echo "Cannot find mas_var.  Set MAS_VAR to the full path to the mas_var binary." >&2
  exit 1
else
  eval $(${MAS_VAR} -s)
fi

source ${MAS_SCRIPT}/mas_library.bash

#END config_header.bash
