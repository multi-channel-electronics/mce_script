#START config_run.bash

# The variable mce_script is the output location
if [ "$mce_script" == "" ]; then
    echo "$0 expects \$mce_script to be defined."
    exit 1
fi

# Hopefully that script exists...

if ! [ -e "$mce_script" ]; then
    echo "Script '$mce_script' does not exist!" >& 2
    exit 1
fi

mce_cmd -qf $mce_script

#END config_run.bash
