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

function float_multiply {
    # Is there a better way to do floating point calcs in bash?
    echo "$1 * $2 + 0.5" | bc | sed 's/\..*//g'
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
    mce_cmd -qpx $@ | sed 's/^.*:\ *//g; s/\ *$//g'
    return ${PIPESTATUS[0]}
}


# Bit decoding

function hex_to_bits {
    arg=$1
    while [ $(( $arg )) -gt 0 ] ; do
	echo -n "$(( $arg & 1 )) "
	arg=$(( $arg / 2 ))
    done
    echo
}

function cards_present {
    hex_to_bits `command_reply "rb cc cards_present"`
}

function rcs_list {
    cards=( `cards_present` )
    rc=1
    for i in `seq 5 -1 2`; do
	[ "${cards[$i]}" == "1" ] && echo -n "rc$rc "
	rc=$(( $rc + 1 ))
    done
    echo
}

# RUNFILE ASSIST

function rcs_cards {
    cards=`command_reply "rb cc rcs_to_report_data"`
    for rc in 1 2 3 4 ; do
	[ "$(( $cards >> $(( 6 - $rc )) & 1 ))" == "1" ] && echo -n " $rc"
    done
    echo
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

# Useful number set manipulation functions


function replace_values {
    # arguments are
    #   original values, new values, new value start position
    # e.g.
    #    replace_values "0 1 2 3 4 5 6" "a b c" 3
    # echos
    #    0 1 2 a b c 6
    orig=( $1 )
    news=( $2 )
    for i in `seq 0 $(( ${#news[@]} - 1 ))` ; do
	orig[$(( $i + $3 ))]=${news[$i]}
    done
    echo ${orig[@]}
}

function repeat_string {
    # arguments are token, repeat count, prefix, postfix, e.g.
    # repeat_string "hat" 8 "here are a bunch of hats: " ""

    echo -n "$3 "
    for a in `seq 1 $2`; do
	echo -n "$1 "
    done
    echo $4
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
