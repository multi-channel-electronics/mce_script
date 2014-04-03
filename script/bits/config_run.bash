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

err_line=( `mce_cmd -qf $mce_script` )
if [ "$?" != "0" ]; then 
    line_no=${err_line[1]}
    echo -e -n "Error on line $line_no of $mce_script:\n    "
    sed ${line_no}'q;d' $mce_script
    exit 1
fi

#END config_run.bash
