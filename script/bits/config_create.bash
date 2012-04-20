#START config_create.bash

create_start=`print_ctime`

mce_script="/tmp/`whoami`_config_mce.scr"

# Remove existing script
[ -e "$mce_script" ] && rm -f "$mce_script"

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
if [ -e "/data/cryo/array_id" ]; then
    array_id=`cat /data/cryo/array_id`
    user_word=`awk "($$1 == \"$array_id\") {print $$2}" $MAS_CONFIG/array_list`
    [ "$user_word" == "" ] && user_word=0
fi
echo "wb cc user_word $user_word" >> $mce_script


#----------------------------------------------
# Readout Cards
#----------------------------------------------
for rc in 1 2 3 4; do
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
	    echo "wb rc$rc flx_quanta$c ${flux_quanta_all[@]:$r_off:$array_width}" >> $mce_script
	else
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


	
done

# echo "Other cards: time=" `print_elapsed $create_start` >&2

#----------------------------------------------
# Address Card
#----------------------------------------------
if [ "$hardware_mux11d" == "0" ]; then 
    echo "wb ac on_bias   ${sq1_bias[@]}" >> $mce_script
    echo "wb ac off_bias  ${sq1_bias_off[@]}" >> $mce_script
else
    echo "wb row select ${row_select[@]}" >> $mce_script
    echo "wb row deselect ${row_deselect[@]}" >> $mce_script
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
