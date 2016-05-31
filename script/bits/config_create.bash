#START config_create.bash

#initialise environment
if [ ! -x ${MAS_VAR:=/usr/mce/bin/mas_var} ]; then
  echo "Cannot find mas_var.  Set MAS_VAR to the full path to the mas_var binary."
  exit 1
else
  eval $(${MAS_VAR} -s)
fi

create_start=`print_ctime`

mce_script=${MAS_TEMP}/`whoami`_config_mce${MAS_MCE_DEV}.scr

# Remove existing script
[ -e "$mce_script" ] && rm -f "$mce_script"

# New file, group rw
umask 002
touch "$mce_script"

# For raveled 2d arrays
AROWS=${array_width}

# Choose sync box parameters:
if [ "$config_sync" != "0" ]; then
    select_clk=$sb1_select_clk
    use_sync=$sb1_use_sync
    use_dv=$sb1_use_dv
else
    select_clk=$sb0_select_clk
    use_sync=$sb0_use_sync
    use_dv=$sb0_use_dv
fi

# Calculate the corrected adc offset.
adc_offset_divided=( adc_offset_c )
for i in `seq 0 $(( ${#adc_offset_c[@]} - 1))` ; do
    adc_offset_divided[$i]=$(( ${adc_offset_c[$i]} / $sample_num ))
done

# Perhaps you don't know about mux11d -- default to off
hardware_mux11d=${hardware_mux11d:-0}

# Allow some flexibility in hardware_fast_sq2 vs. hardware_bac
if [ "$hardware_fast_sq2" == "" ]; then
    hardware_fast_sq2=${hardware_bac}
fi

#----------------------------------------------
# sys commands
#----------------------------------------------
echo "wb sys row_len $row_len" >> $mce_script
echo "wb sys num_rows $num_rows" >> $mce_script

if [ "$hardware_rect" == "0" ]; then
    # Pre-v5 firmware
    echo "wb cc num_rows_reported $num_rows_reported" >> $mce_script
else
    # v5 and later (rectangle mode)
    echo "wb cc num_rows_reported $num_rows_reported" >> $mce_script
    echo "wb cc num_cols_reported 8" >> $mce_script
    echo "wb rca num_rows_reported $num_rows_reported" >> $mce_script
    echo "wb rca num_cols_reported 8" >> $mce_script
    echo "wb rca readout_row_index 0" >> $mce_script
    echo "wb rca readout_col_index 0" >> $mce_script
fi

#----------------------------------------------
# Clock Card
#----------------------------------------------
echo "wb cc data_rate $data_rate" >> $mce_script
echo "wb cc select_clk $select_clk" >> $mce_script
echo "wb cc use_dv $use_dv" >> $mce_script
echo "wb cc use_sync $use_sync" >> $mce_script
echo "wb cc ret_dat_s 1 1" >> $mce_script

if [ "$hardware_rect" != "0" ]; then
    # Assemble bits for choosing readout cards to report data
    bit=0x20  # RC1
    rc_bits=0
    for i in `seq 0 3`; do
        if [ "${hardware_rc_data[$i]}" != "0" ]; then
            rc_bits=$(( $rc_bits + $bit ))
        fi
        bit=$(( $bit / 2 ))
    done
    echo "wb cc rcs_to_report_data $rc_bits" >> $mce_script
fi

# Write cc user_word based on array_id - this shows up in frame data
user_word=0
if [ -e "${MAS_DATA_ROOT}/array_id" ]; then
    array_id=`cat ${MAS_DATA_ROOT}/array_id`
    user_word=`awk "($$1 == \"$array_id\") {print $$2}" $MAS_CONFIG/array_list`
    [ "$user_word" == "" ] && user_word=0
fi
echo "wb cc user_word $user_word" >> $mce_script


#----------------------------------------------
# Readout Cards
#----------------------------------------------
## Mask out SA and SQ2 bias for bad columns.
vals=${sa_bias[@]}
mask=${columns_off[@]}
sa_bias=( `mask_values "$vals" "$mask" 1 0` )

vals=${sq2_bias[@]}
mask=${columns_off[@]}
sq2_bias=( `mask_values "$vals" "$mask" 1 0` )

for rc in 1 2 3 4; do
    min_flux_quantum=999999
    max_gaini=0
    [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue
    [ "${hardware_rc[$(( $rc - 1 ))]}" == "0" ] && continue

    ch_ofs=$(( ($rc-1)*8 ))
#    echo "Readout card $rc: time=" `print_elapsed $create_start` >&2

    echo "wb rc$rc readout_row_index $readout_row_index" >> $mce_script
    echo "wb rc$rc readout_col_index 0" >> $mce_script
    echo "wb rc$rc sample_dly   $sample_dly" >> $mce_script
    echo "wb rc$rc sample_num   $sample_num" >> $mce_script
    echo "wb rc$rc fb_dly       $fb_dly" >> $mce_script
    echo "wb rc$rc fb_const    " `repeat_string $fb_const 8` >> $mce_script
    echo "wb rc$rc data_mode    $data_mode" >> $mce_script
    echo "wb rc$rc sa_bias      ${sa_bias[@]:$ch_ofs:8}" >> $mce_script
    echo "wb rc$rc offset       ${sa_offset[@]:$ch_ofs:8}" >> $mce_script

    # Don't auto-servo columns flagged in "columns_off"
    if [ "$servo_mode" == "3" ]; then
        echo -n "wb rc$rc servo_mode  "
        for c in `seq 0 7`; do
            chan=$(( $c + $ch_ofs ))
            if [ "${columns_off[$chan]}" == "1" ]; then
                echo -n " 1"
            else
                echo -n " 3"
            fi
        done
        echo
    else
        # Servo modes other than 3 are not affected by columns_off
        echo "wb rc$rc servo_mode   " `repeat_string $servo_mode 8`
    fi >> $mce_script

    # Servo parameters, including dead and frail detector turn-offs
    for c in `seq 0 7`; do
        chan=$(( $c + $ch_ofs ))
        dead_ofs=$(( ($c + $ch_ofs)*$array_width ))

        if [ "${columns_off[$chan]}" != "1" -a $chan -lt $num_rows ]; then
            if [ ${servo_i[$chan]} -gt $max_gaini ]; then
                max_gaini=${servo_i[$chan]}
            fi
        fi

        p_terms=( `repeat_string ${servo_p[$chan]} $array_width` )
        i_terms=( `repeat_string ${servo_i[$chan]} $array_width` )
        d_terms=( `repeat_string ${servo_d[$chan]} $array_width` )

        if [ "$config_frail_tes" == "0" ]; then
            for r in `seq 0 $(( $array_width - 1 ))`; do
                if [ "${frail_detectors[$(( $dead_ofs + $r ))]}" != "0" ]; then
                    p_terms[$r]=$frail_servo_p
                    i_terms[$r]=$frail_servo_i
                    d_terms[$r]=$frail_servo_d
                fi
            done
        fi

        if [ "$config_dead_tes" == "0" ]; then
            for r in `seq 0 $(( $array_width - 1 ))`; do
                if [ "${dead_detectors[$(( $dead_ofs + $r ))]}" != "0" ]; then
                    p_terms[$r]=0
                    i_terms[$r]=0
                    d_terms[$r]=0
                fi
            done
        fi

        echo "wb rc$rc gainp$c ${p_terms[@]}" >> $mce_script
        echo "wb rc$rc gaini$c ${i_terms[@]}" >> $mce_script
        echo "wb rc$rc gaind$c ${d_terms[@]}" >> $mce_script
    done

    # Flux jump quanta, and enable/disable
    for c in `seq 0 7`; do
        chan=$(( $c +  $ch_ofs ))
        r_off=$(( $array_width * $chan ))

        if [ "${config_flux_quanta_all}" != "0" ]; then
	    if [ "$config_dead_tes" == "0" ]; then
		for r in `seq 0 $(( $num_rows - 1 ))`; do
		    if [ "${dead_detectors[$(( $r_off + $r ))]}" == "0" \
			-a ${flux_quanta_all[$(( $r_off + $r ))]} -lt $min_flux_quantum \
			-a ${flux_quanta_all[$(( $r_off + $r ))]} -gt 0 ]; then
			min_flux_quantum=${flux_quanta_all[$(( $r_off + $r ))]}
		    fi
		done
	    else
		min_flux_quantum=`find_min_positive ${min_flux_quantum} ${flux_quanta_all[@]:$r_off:$num_rows}`
	    fi
            echo "wb rc$rc flx_quanta$c ${flux_quanta_all[@]:$r_off:$num_rows}" >> $mce_script
        else
            if [ ${flux_quanta[$chan]} -lt ${min_flux_quantum} \
              -a ${flux_quanta[$chan]} -gt 0 ]; then
                min_flux_quantum=${flux_quanta[$chan]}
            fi
            repeat_string "${flux_quanta[$chan]}" $AROWS "wb rc$rc flx_quanta$c" >> $mce_script
        fi

        if [ "${config_adc_offset_all}" != "0" ]; then
            echo "wb rc$rc adc_offset$c ${adc_offset_cr[@]:$r_off:$array_width}" >> $mce_script
        else
            repeat_string "${adc_offset_divided[$chan]}" $AROWS "wb rc$rc adc_offset$c" >> $mce_script
        fi
    done

    # Readout filter
    if [ "$config_filter" == "1" ]; then
        echo "wb rca fltr_coeff ${filter_params[@]}" >> $mce_script
    fi

    echo "wb rc$rc en_fb_jump $flux_jumping" >> $mce_script

    # integral clamp

    if [ "$config_integral_clamp" == "1" ]; then
        # don't divide by zero
        if [ $max_gaini == "0" ]; then
            integral_clamp=0
        elif [ $flux_jumping == "1" ]; then
            integral_clamp=$(printf %i $(echo "$integral_clamp_factor * 127 * 4096 * $min_flux_quantum / $max_gaini" | bc))
        else
            integral_clamp=$(printf %i $(echo "$integral_clamp_factor * 8192 * 4096 / $max_gaini" | bc))
        fi
        echo "wb rc$rc integral_clamp $integral_clamp" >> $mce_script
    fi
done

# echo "Other cards: time=" `print_elapsed $create_start` >&2

#----------------------------------------------
# Address Card
#----------------------------------------------

# I wanted to put this below next to ac enbl_mux, but a cryptic
# comment in the bc section of this script makes it sound like enbl
# needs to be sent to the bc before sending the values for the DACs.
# So putting it here, in advance.
if [ "$mux11d_hybrid_row_select" == "1" ]; then
    for i in `seq 0 $((${#mux11d_row_select_cards[@]}-1))`; do
	card=${mux11d_row_select_cards[$i]}
	r0=${mux11d_row_select_cards_row0[$i]}
	for j in `seq 3`; do
	    if [ "$card" == "bc$j" ]; then
		for k in `seq 0 $((${#mux11d_mux_order[@]}-1))`; do
		    rsmr0=$((${mux11d_mux_order[k]}-$r0))
		    if [ \( "${rsmr0}" -ge "0" \) -a \( "${rsmr0}" -lt "32" \) ]; then
			echo "wra ${card} enbl_mux ${rsmr0} 1" >> $mce_script
		    fi
		done
	    fi
	done
    done
fi


if [ "$hardware_mux11d" == "0" ]; then
    echo "wb ac on_bias   ${sq1_bias[@]}" >> $mce_script
    echo "wb ac off_bias  ${sq1_bias_off[@]}" >> $mce_script
else
    if [ "$mux11d_hybrid_row_select" == "1" ]; then
	## Hybridized muxing - prep ac on_bias/off_bias lines
	if [ ${#mux11d_row_select_cards[@]} != ${#mux11d_row_select_cards_row0[@]} ]; then
	    # Nonsensical configuration.  Give up...
	    echo "Length of mux11d_row_select_cards=(${mux11d_row_select_cards[@]}) and mux11d_row_select_cards_row0=(${#mux11d_row_select_cards_row0[@]}) arrays not equal.  Abort!"
	    exit 1
	else 
	    # Loop through the MCE Cards we're hybridizing the row
	    # selects over and deal with them one at a time.  Really
	    # only two cases; AC or BC.
            for i in `seq 0 $((${#mux11d_row_select_cards[@]}-1))`; do
		card=${mux11d_row_select_cards[$i]}
		r0=${mux11d_row_select_cards_row0[$i]}

		## For now, will assume user has correctly spaced r0
		## for the cards; ie, AC has 41 or more indices
		## between it and the r0 for the next card, and BCs
		## have 32 or more indicies between them and the r0
		## for the next card.
		
		#
		# Configure AC-driven row selects
		if [ "$card" == "ac" ]; then
		    # These will be written to ac on_bias and ac
		    # off_bias
		    hybrid_ac_on_bias=(`repeat_string 0 41`)
		    hybrid_ac_off_bias=(`repeat_string 0 41`)
		    for k in `seq 0 $((${#mux11d_mux_order[@]}-1))`; do

			# don't go higher than # of rows
                        if [ $k -gt $(( $num_rows - 1 )) ]; then
                            continue
                        fi

			rsmr0=$((${mux11d_mux_order[k]}-$r0))
			if [ \( "${rsmr0}" -ge "0" \) -a \( "${rsmr0}" -lt "41" \) ]; then
			    # If there is no row select for this
			    # entry, throw an exception, unless it's
			    # the AC idle row
			    if [ ! "$k" -lt "${#row_select[@]}" ]; then
				if [ "${mux11d_mux_order[k]}" -eq "${mux11d_ac_idle_row}" ]; then
				    continue
				fi
				# Not the AC idle row.  Exception!
				echo "The row_select (size=${#row_select[@]}) and row_deselect (size=${#row_deselect[@]})"
				echo "lists are shorter than the mux11d_mux_order (size=${#mux11d_mux_order[@]}) list in"
				echo "experiment.cfg, and the row with no corresponding select/deselect is *not* the AC"
				echo "idle row.  (k=${k} r0=${r0} rsmr0=${rsmr0} row_select[$k]=${row_select[$k]}"
				echo "row_deselect[$k]=${row_deselect[$k]}).  Abort!"
				exit 1
			    else
				hybrid_ac_on_bias[${rsmr0}]=${row_select[$k]}
				hybrid_ac_off_bias[${rsmr0}]=${row_deselect[$k]}
			    fi
			fi
		    done

		    echo "wb ac on_bias   ${hybrid_ac_on_bias[@]}" >> $mce_script
		    echo "wb ac off_bias  ${hybrid_ac_off_bias[@]}" >> $mce_script
		fi
		# Done configuring AC-driven row selects

		#
		# Configure BC-driven row selects
		for j in `seq 3`; do
		    if [ "$card" == "bc$j" ]; then
			for k in `seq 0 $((${#mux11d_mux_order[@]}-1))`; do
			    rsmr0=$((${mux11d_mux_order[k]}-$r0))
			    if [ \( "${rsmr0}" -ge "0" \) -a \( "${rsmr0}" -lt "32" \) ]; then
				hybrid_bc_fb_col=(`repeat_string ${row_deselect[$k]} $AROWS`)
				hybrid_bc_fb_col[$k]=${row_select[$k]}
				echo "wb bc$j fb_col${rsmr0}   ${hybrid_bc_fb_col[@]}" >> $mce_script
			    fi
			done
		    fi
		done
		# Done configuring BC-driven row selects
		#

	    done
	fi
    else # Just using ac on_bias/off_bias to switch mux11d rows
	# Must take ac row order into account ... row select/deselect
	# are really just synonyms for ac on_bias/off_bias
	for rs in `seq 0 $((${#row_order[@]}-1))`; do
	    echo "wra ac on_bias ${row_order[${rs}]} ${row_select[${rs}]}" >> $mce_script
	    echo "wra ac off_bias ${row_order[${rs}]} ${row_deselect[${rs}]}" >> $mce_script
	done
    fi
fi

echo "wb ac row_dly   $row_dly" >> $mce_script
echo "wb ac row_order ${row_order[@]}" >> $mce_script
echo "wb ac enbl_mux  1" >> $mce_script

# Set the TES biases via the "tes bias" virtual address
if [ "$tes_bias_do_reconfig" != "0" ]; then
    echo "wb tes bias ${tes_bias[@]}" >> $mce_script
fi

#----------------------------------------------
# Bias Cards - use functional mappings!
#----------------------------------------------

# Set enbl_mux before writing per-column values, since DACs need to be
# kicked once after enbl_mux is turned off.

# For biasing address card, set the correct mux_mode and row_order
# But only if we're not mux11d.
if [ "$hardware_mux11d" == "0" ]; then

    if [ "$hardware_fast_sq2" == "1" ]; then
        echo "wb bac row_order ${row_order[@]}" >> $mce_script
        echo "wb bac enbl_mux 2" >> $mce_script
    fi

    # For new bias card in fast_sq2 mode, set enbl_mux for all columns
    if [ "$hardware_fast_sq2" == "2" ]; then
        for rc in 1 2 3 4; do
            [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue
            ch_ofs=$(( ($rc-1)*8 ))
            echo "wra sq2 enbl_mux $ch_ofs `repeat_string $config_fast_sq2 8`" >> $mce_script
        done
    fi
fi

#Still only write the relevant columns depending on readout card configuration
for rc in 1 2 3 4; do
    [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue

    ch_ofs=$(( ($rc-1)*8 ))

    if [ "$hardware_mux11d" == "0" ]; then

        echo "wra sa  fb    $ch_ofs  ${sa_fb[@]:$ch_ofs:8}"
        echo "wra sq2 bias  $ch_ofs  ${sq2_bias[@]:$ch_ofs:8}"

        # SQ2 feedback
        if [ "$config_fast_sq2" == "0" ]; then
            if [ "$hardware_fast_sq2" == "1" ]; then
                # Emulate bias card with a BAC
                for a in `seq 0 7`; do
                    c=$(( $ch_ofs + $a ))
                    repeat_string "${sq2_fb[$c]}" $AROWS "wb bac fb_col$c"
                done
            else
                # People still use bias cards?
                echo "wra sq2 fb    $ch_ofs  ${sq2_fb[@]:$ch_ofs:8}"
            fi
        else
            # BAC and new bias card firmware support sq2 fb_col%
            for a in `seq 0 7`; do
                row_ofs=$(( ($ch_ofs+$a) * $AROWS ))
                echo "wb sq2 fb_col$(( $a + $ch_ofs )) ${sq2_fb_set[@]:$row_ofs:$AROWS}"
            done
        fi
    else
        # SA FB, possibly fast-switching
        echo "wra sa enbl_mux $ch_ofs `repeat_string $config_fast_sa_fb 8`"
        if [ "$config_fast_sa_fb" == "1" ]; then
            for a in `seq 0 7`; do
                row_ofs=$(( ($ch_ofs+$a) * $AROWS ))
                echo "wb sa fb_col$(( $a + $ch_ofs )) ${sa_fb_set[@]:$row_ofs:$AROWS}"
            done
        else
            echo "wra sa fb $ch_ofs  ${sa_fb[@]:$ch_ofs:8}"
        fi
        # SQ1 bias, possibly fast-switching
        echo "wra sq1 enbl_mux $ch_ofs `repeat_string $config_fast_sq1_bias 8`"
        if [ "$config_fast_sq1_bias" == "1" ]; then
            for a in `seq 0 7`; do
                row_ofs=$(( ($ch_ofs+$a) * $AROWS ))
                echo "wb sq1 bias_col$(( $a + $ch_ofs )) ${sq1_bias_set[@]:$row_ofs:$AROWS}"
            done
        else
            echo "wra sq1 bias $ch_ofs  ${sq1_bias[@]:$ch_ofs:8}"
        fi
    fi >> $mce_script
done

# Servo loop re-init

for rc in 1 2 3 4; do
    [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue
    echo "wb rc$rc flx_lp_init 1" >> $mce_script
done

#END config_create.bash
