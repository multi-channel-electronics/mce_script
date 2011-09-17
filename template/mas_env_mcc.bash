#!/bin/bash

# MAS profile script for the MCE Control Computer.

if [ "$MAS_ROOT" == "" ]; then
	export MAS_ROOT=/usr/mce/mce_script
fi

#Trailing slashes are recommended

export MAS_BIN=/usr/mce/bin/
if [ -d /data/tmp ]; then
	export MAS_TEMP=/data/tmp/
else
	export MAS_TEMP=/tmp/
fi
export MAS_DATA=/data/cryo/current_data/

export MAS_TEMPLATE=${MAS_ROOT}/template/
export MAS_SCRIPT=${MAS_ROOT}/script/
export MAS_TEST_SUITE=${MAS_ROOT}/test_suite/
export MAS_IDL=${MAS_ROOT}/idl_pro/
export MAS_PYTHON=${MAS_ROOT}/python/

export MAS_CONFIG=${MAS_TEMPLATE}

export PATH=${PATH}:${MAS_BIN}:${MAS_SCRIPT}:${MAS_TEST_SUITE}
export PYTHONPATH=${PYTHONPATH}:${MAS_PYTHON}
