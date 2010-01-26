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


if [ "$tune_id" == "" ]; then
    # No tuning, so no runfile block
    SOURCE_TUNE=/dev/null
else
    SOURCE_TUNE=/data/cryo/${tune_id}
fi

# Change the last_squid_tune link
LAST_TUNE=/data/cryo/last_squid_tune

# ... but only if everything seems reasonable.
if [ -e "$SOURCE_TUNE" ] && ! [ -d "$SOURCE_TUNE" ] && ( \
    ( [ -h "$LAST_TUNE" ] && rm "$LAST_TUNE" ) || \
    ! [ -e "$LAST_TUNE" ] ); then
    ln -s "$SOURCE_TUNE" "$LAST_TUNE"
else
    echo "Problem linking $SOURCE_TUNE to $LAST_TUNE" >& 2
    exit 1
fi

#END config_run.bash
