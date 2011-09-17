#!/bin/tcsh

# Come on, who uses csh these days...

if ( "$MAS_ROOT" == "" ) then
    setenv MAS_ROOT /usr/mce/mce_script
endif

#Trailing slashes are recommended

setenv MAS_BIN /usr/mce/bin/
setenv MAS_TEMP /tmp/
setenv MAS_DATA /data/cryo/current_data/

setenv MAS_TEMPLATE ${MAS_ROOT}/template/
setenv MAS_SCRIPT ${MAS_ROOT}/script/
setenv MAS_TEST_SUITE ${MAS_ROOT}/test_suite/
setenv MCE_JAM_DIR ${MAS_ROOT}/firmware/
setenv MAS_IDL ${MAS_ROOT}/idl_pro/
setenv MAS_PYTHON ${MAS_ROOT}/python/

setenv MAS_CONFIG ${MAS_TEMPLATE}

setenv PATH ${PATH}:${MAS_BIN}:${MAS_SCRIPT}:${MAS_TEST_SUITE}
