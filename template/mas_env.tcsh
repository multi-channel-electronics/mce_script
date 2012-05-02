#!/bin/tcsh

# Come on, who uses csh these days...

#unset volitile variables
unsetenv MAS_BIN
unsetenv MAS_TEMP
unsetenv MAS_DATA_ROOT
unsetenv MAS_DATA

unsetenv MAS_IDL
unsetenv MAS_PYTHON
unsetenv MAS_TEMPLATE
unsetenv MAS_TEST_SUITE

#initialise environment
if ( { test -z $MAS_VAR } ) then
  setenv MAS_VAR /usr/mce/bin/mas_var
endif

if ( { test \! -x $MAS_VAR } ) then
  echo "Cannot find mas_var.  Set MAS_VAR to the full path to the mas_var binary." >&2
  exit 1
else
  eval `$MAS_VAR -c`
endif
