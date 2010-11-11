#START config_header.bash

# Do not set MAS environment!  Just source the library
if [ "$MAS_ROOT" == "" ]; then
	echo MAS_ROOT not defined. >&2
	exit 1
fi

source ${MAS_SCRIPT}/mas_library.bash

#END config_header.bash
