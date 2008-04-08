#START config_create.bash

create_start=`print_ctime`

# The variable mce_script is the output location
if [ "$mce_script" == "" ]; then
	echo "$0 expects \$mce_script to be defined."
	exit 1
fi

# Remove existing script
[ -e "$mce_script" ] && rm "$mce_script"

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

# For readability, translate config_rc[0-3] to config_rc1-4

config_rc1=${config_rc[0]}
config_rc2=${config_rc[1]}
config_rc3=${config_rc[2]}
config_rc4=${config_rc[3]}

#----------------------------------------------
# sys commands  
#----------------------------------------------
echo "wb sys row_len $row_len" >> $mce_script
echo "wb sys num_rows $num_rows" >> $mce_script

#----------------------------------------------
# Clock Card
#----------------------------------------------
echo "wb cc num_rows_reported $num_rows_reported" >> $mce_script
echo "wb cc data_rate $data_rate" >> $mce_script
echo "wb cc select_clk $select_clk" >> $mce_script
echo "wb cc use_dv $use_dv" >> $mce_script
echo "wb cc use_sync $use_sync" >> $mce_script
echo "wb cc ret_dat_s 1 1" >> $mce_script

# Write cc user_word based on array_id - this shows up in frame data
if [ -e "/data/cryo/array_id" ]; then
    array_id=`cat /data/cryo/array_id`
    case "$array_id" in
	"AR1")
	echo "wb cc user_word 1" >> $mce_script
	;;
	"AR2")
	echo "wb cc user_word 2" >> $mce_script
	;;
	"AR3")
	echo "wb cc user_word 3" >> $mce_script
	;;
	*)
	echo "wb cc user_word 0" >> $mce_script
	;;
    esac
fi


#----------------------------------------------
# Readout Cards
#----------------------------------------------
for rc in 1 2 3 4; do
    [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue
    
    ch_ofs=$(( ($rc-1)*8 ))
#    echo "Readout card $rc: time=" `print_elapsed $create_start` >&2
    
    echo "wb rc$rc en_fb_jump   0" >> $mce_script
    echo "wb rc$rc readout_row_index $readout_row_index" >> $mce_script
    echo "wb rc$rc sample_dly   $sample_dly" >> $mce_script
    echo "wb rc$rc sample_num   $sample_num" >> $mce_script
    echo "wb rc$rc fb_dly       $fb_dly" >> $mce_script
    echo "wb rc$rc fb_const     " `repeat_string $fb_const 8` >> $mce_script
    echo "wb rc$rc servo_mode   " `repeat_string $servo_mode 8` >> $mce_script
    echo "wb rc$rc data_mode    $data_mode" >> $mce_script
    echo "wb rc$rc sa_bias      ${sa_bias[@]:$ch_ofs:8}" >> $mce_script
    echo "wb rc$rc offset       ${sa_offset[@]:$ch_ofs:8}" >> $mce_script
    for c in `seq 0 7`; do 
	chan=$(( $c +  $ch_ofs ))
	repeat_string "${flux_quanta[$chan]}" 41 "wb rc$rc flx_quanta$c" >> $mce_script

	if [ "${config_adc_offset_all}" != "0" ]; then
	    r_off=$(( $array_width * $chan ))
	    echo "wb rc$rc adc_offset$c ${adc_offset_cr[@]:$r_off:$array_width}" >> $mce_script
	else
	    repeat_string "${adc_offset_divided[$chan]}" 41 "wb rc$rc adc_offset$c" >> $mce_script
	fi
    done

    #
    for c in `seq 0 7`; do
	chan=$(( $c + $ch_ofs ))
	dead_ofs=$(( ($c + $ch_ofs)*$array_width ))
	
	p_terms=( `repeat_string ${servo_p[$chan]} $array_width` )
	i_terms=( `repeat_string ${servo_i[$chan]} $array_width` )
	d_terms=( `repeat_string ${servo_d[$chan]} $array_width` )

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
	
done

# echo "Other cards: time=" `print_elapsed $create_start` >&2

#----------------------------------------------
# Address Card
#----------------------------------------------
echo "wb ac row_dly   $row_dly" >> $mce_script
echo "wb ac row_order ${row_order[@]}" >> $mce_script
echo "wb ac on_bias   ${sq1_bias[@]}" >> $mce_script
echo "wb ac enbl_mux  1" >> $mce_script


# Set the TES biases via the "tes bias" virtual address
echo "wb tes bias ${tes_bias[@]}" >> $mce_script

#----------------------------------------------
# Bias Cards - use functional mappings!
#----------------------------------------------

#Still only write the relevant columns depending on readout card configuration
for rc in 1 2 3 4; do
    [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue
 
    ch_ofs=$(( ($rc-1)*8 ))
    echo "wra sa  fb    $ch_ofs  ${sa_fb[@]:$ch_ofs:8}"    >> $mce_script
    echo "wra sq2 bias  $ch_ofs  ${sq2_bias[@]:$ch_ofs:8}" >> $mce_script

    if [ "$hardware_bac" == "0" ]; then
	echo "wra sq2 fb    $ch_ofs  ${sq2_fb[@]:$ch_ofs:8}"   >> $mce_script
    else
	for a in `seq 0 7`; do
	    row_ofs=$(( ($ch_ofs+$a) * 41 ))
	    echo "wb sq2 fb_col$(( $a + $ch_ofs )) ${sq2_fb_set[@]:$row_ofs:41}" >> $mce_script
	done
    fi
done

# For biasing address card, set the correct mux_mode and row_order
if [ "$hardware_bac" != "0" ]; then
    echo "wb bac row_order ${row_order[@]}" >> $mce_script
    echo "wb bac enbl_mux 2" >> $mce_script
fi

#---------------------------------------------------------------
# Flux Jumping
#---------------------------------------------------------------

# Flux jumps occur when the 1st stage fb reaches 3/4 of the positive
# or negative range of the 14-bit ADC. The flux qanta can correct the
# 1st stage fb by up to 6/4 of the half-range before is triggers
# corrective counter-jump.

for rc in 1 2 3 4; do
    [ "${config_rc[$(( $rc - 1 ))]}" == "0" ] && continue

    echo "wb rc$rc en_fb_jump 0" >> $mce_script
    echo "wb rc$rc flx_lp_init 1" >> $mce_script
done

#END config_create.bash
