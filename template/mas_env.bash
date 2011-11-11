#!/bin/bash

# To run mce_script with a non-standard MAS install, point MAS_CONFIG to
# the associated mas_config program
if [ -z "$MAS_CONFIG" ]; then
  export MAS_CONFIG=/usr/mce/bin/mas_config
fi
