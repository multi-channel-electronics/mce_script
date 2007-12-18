#!/bin/bash

NULLF=/dev/null

# FUNCTIONS FOR TIME PROFILING #

function print_ctime {
	date -u +%s
}

function print_elapsed {
	echo $(( `print_ctime` - $1 ))
}

function to_hex {
    echo "10i ${1} 16o p"|dc
}

function to_dec {
    echo "16i ${1} p"|dc
}

# FUNCTIONS FOR DSP DIAGNOSTIC #

function print_pci_mem {
    dsp_cmd -pqx read $1 $2 | cut -f 5 -d ' '
}  

function print_dsp_version {
    print_pci_mem X 3
}

function print_dsp_diagnostic {
    dsp_ver=`print_dsp_version`
    case $dsp_ver in
	
	"0X550103" | "0x550103")  # U.01.03
	    echo -n "U.01.03 - PCI error count = "
	    print_pci_mem X 0x47
	    ;;
	
	"0X550104" | "0x550104")  # U.01.04
	    echo -n "U.01.04 - PCI error count = "
	    print_pci_mem X 0x47
	    ;;
	
	* )
	    echo "No diagnostic for DSP version $dsp_ver"
	    ;;

    esac
}


# MCE COMMAND REPLY PARSERS

function command_reply {
    mce_cmd -qpx $@ | cut -d ':' -f 2
}


# HEALTH CHECKS - return 0 if system appears healthy

function check_reset {
    num_rows=`fixme!`
    my_num_rows=( `command_reply RB sys num_rows` )
    err=$?
    if [ "$err" != "0" ]; then
	return $err
    fi
    if [ "$num_rows" != "${my_num_rows[0]}" ]; then
	return 1
    fi
}

function write_back_test {
    # $1 is list of cards

    for c in $1; do

	command_reply WB $c led 7
	a=`command_reply RB $c led`

	command_reply WB $c led 7
	b=`command_reply RB $c led`

	s=$(( $a + $b ))
	if [ "$s" != "7" ]; then
	    echo "write_back_test failed on card $c: $a + $b = $s"
	    return 1
	fi
	  
    done
}



# HEALTH FIXES - return 0 if fix probably succeeded


function health_clear {
    # Should not fail if MCE has been reset
    
    # Example:
    return 0
}

# function count_failures {
#   if [ $failures -ge $max_failures ]; then
#       echo "$scrn : too many failures!"
# 	      return 1
#   fi
#   return 0
# }
