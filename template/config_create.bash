#START config_create.bash

# The variable mce_script is the output location
if [ "$mce_script" == "" ]; then
	echo "$0 expects \$mce_script to be defined."
	exit 1
fi


# Choose sync box parameters:
if [ $config_sb ]; then
	select_clock=$sb1_select_clk
	use_sync=$sb1_use_sync
	use_db=$sb1_use_db
else
	select_clock=$sb0_select_clk
	use_sync=$sb0_use_sync
	use_db=$sb0_use_db
fi

# Calculate the corrected adc offset.
adc_offset_divided=( adc_offset )
for i in `seq 0 $(( ${#adc_offset[@]} - 1))` ; do
	adc_offset_divided[$i]=$(( ${adc_offset[$i]} / $sample_num ))
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

#----------------------------------------------
# Readout Cards
#----------------------------------------------

if [ $config_rc1 ]; then
    #note that pidz are set by pidz_dead_off script separately
    # Disable flux-jumping 
    echo "wb rc1 en_fb_jump   0" >> $mce_script
    echo "wb rc1 readout_row_index $readout_row_index" >> $mce_script
    echo "wb rc1 sample_dly   $sample_dly" >> $mce_script
    echo "wb rc1 sample_num   $sample_num" >> $mce_script
    echo "wb rc1 fb_dly       $fb_dly" >> $mce_script
    echo "wb rc1 fb_const     " `repeat_string $fb_const 8` >> $mce_script
    echo "wb rc1 servo_mode   " `repeat_string $servo_mode 8` >> $mce_script
    echo "wb rc1 data_mode    $data_mode" >> $mce_script
    echo "wb rc1 sa_bias      ${sa_bias[@]:0:8}" >> $mce_script
    echo "wb rc1 offset       ${sa_offset[@]:0:8}" >> $mce_script
    for c in `seq 0 7`; do 
	chan=$(( $c +  0 ))
	echo "wb rc1 flx_quanta$c " `repeat_string ${flux_quanta[$chan]} 41` >> $mce_script
	echo "wb rc1 adc_offset$c " `repeat_string ${adc_offset_divided[$chan]} 41` >> $mce_script
    done

    pidz_dead_off $servo_p $servo_i $servo_d 1 >> $mce_script

fi

if [ $config_rc2 ]; then
    #note that pidz are set by pidz_dead_off script separately
    # Disable flux-jumping 
    echo "wb rc2 en_fb_jump   0" >> $mce_script
    echo "wb rc2 readout_row_index $readout_row_index" >> $mce_script
    echo "wb rc2 sample_dly   $sample_dly" >> $mce_script
    echo "wb rc2 sample_num   $sample_num" >> $mce_script
    echo "wb rc2 fb_dly       $fb_dly" >> $mce_script
    echo "wb rc2 fb_const     " `repeat_string $fb_const 8` >> $mce_script
    echo "wb rc2 servo_mode   " `repeat_string $servo_mode 8` >> $mce_script
    echo "wb rc2 data_mode    $data_mode" >> $mce_script
    echo "wb rc2 sa_bias      ${sa_bias_rc2[@]}" >> $mce_script
    echo "wb rc2 offset       ${sa_offset_rc2[@]}" >> $mce_script
    for c in `seq 0 7`; do
	echo "wb rc2 flx_quanta$c " `repeat_string ${flux_quanta_rc2[$c]} 41` >> $mce_script
    done
    for c in `seq 0 7`; do
	echo "wb rc2 adc_offset$c " `repeat_string ${adc_offset_divided[$(( $c +  8 ))]} 41` >> $mce_script
    done

    pidz_dead_off $servo_p $servo_i $servo_d 2 >> $mce_script

fi

if [ $config_rc3 ]; then
    #note that pidz are set by pidz_dead_off script separately
    # Disable flux-jumping 
    echo "wb rc3 en_fb_jump   0" >> $mce_script
    echo "wb rc3 readout_row_index $readout_row_index" >> $mce_script
    echo "wb rc3 sample_dly   $sample_dly" >> $mce_script
    echo "wb rc3 sample_num   $sample_num" >> $mce_script
    echo "wb rc3 fb_dly       $fb_dly" >> $mce_script
    echo "wb rc3 fb_const     " `repeat_string $fb_const 8` >> $mce_script
    echo "wb rc3 servo_mode   " `repeat_string $servo_mode 8` >> $mce_script
    echo "wb rc3 data_mode    $data_mode" >> $mce_script
    echo "wb rc3 sa_bias      ${sa_bias_rc3[@]}" >> $mce_script
    echo "wb rc3 offset       ${sa_offset_rc3[@]}" >> $mce_script
    for c in `seq 0 7`; do
	echo "wb rc3 flx_quanta$c " `repeat_string ${flux_quanta_rc3[$c]} 41` >> $mce_script
    done
    for c in `seq 0 7`; do
	echo "wb rc3 adc_offset$c " `repeat_string ${adc_offset_divided[$(( $c + 26 ))]} 41` >> $mce_script
    done

    pidz_dead_off $servo_p $servo_i $servo_d 3 >> $mce_script

fi

if [ $config_rc4 ]; then
    #note that pidz are set by pidz_dead_off script separately
    # Disable flux-jumping 
    echo "wb rc4 en_fb_jump   0" >> $mce_script
    echo "wb rc4 readout_row_index $readout_row_index" >> $mce_script
    echo "wb rc4 sample_dly   $sample_dly" >> $mce_script
    echo "wb rc4 sample_num   $sample_num" >> $mce_script
    echo "wb rc4 fb_dly       $fb_dly" >> $mce_script
    echo "wb rc4 fb_const     " `repeat_string $fb_const 8` >> $mce_script
    echo "wb rc4 servo_mode   " `repeat_string $servo_mode 8` >> $mce_script
    echo "wb rc4 data_mode    $data_mode" >> $mce_script
    echo "wb rc4 sa_bias      ${sa_bias_rc4[@]}" >> $mce_script
    echo "wb rc4 offset       ${sa_offset_rc4[@]}" >> $mce_script
    for c in `seq 0 7`; do
	echo "wb rc4 flx_quanta$c " `repeat_string ${flux_quanta_rc4[$c]} 41` >> $mce_script
    done
    for c in `seq 0 7`; do
	echo "wb rc4 adc_offset$c " `repeat_string ${adc_offset_divided[$(( $c + 24 ))]} 41` >> $mce_script
    done

    pidz_dead_off $servo_p $servo_i $servo_d 4 >> $mce_script

fi

# Run the adc_offset config file.
#today=`cat /data/cryo/current_data_name`
#$MAS_DATA/config_mce_adc_offset_${today} >> $mce_script
#if [ $? ]; then
#  echo "$0 failed: config_mce_adc_offset_${today} failed with code $cmdstatus, config aborted..." >&2
#  exit 2
#fi

#----------------------------------------------
# Address Card
#----------------------------------------------
echo "wb ac row_dly   $row_dly" >> $mce_script
echo "wb ac row_order ${row_order[@]}" >> $mce_script
echo "wb ac on_bias   ${sq1bias[@]}" >> $mce_script
echo "wb ac enbl_mux  $enbl_mux" >> $mce_script


#----------------------------------------------
# Bias Card 1 (flux_fb on BC1 sets sa_fb)
#----------------------------------------------
#echo "wb bc1 flux_fb $safb0 $safb1 $safb2 $safb3 $safb4 $safb5 $safb6 $safb7 $safb8 $safb9 $safb10 $safb11 $safb12 $safb13 $safb14 $safb15 $safb16 $safb17 $safb18 $safb19 $safb20 $safb21 $safb22 $safb23 $safb24 $safb25 $safb26 $safb27 $safb28 $safb29 $safb30 $safb31" >> $mce_script
echo "wb bc1 bias $tes_bias_bc1" >> $mce_script
                                                                                                                             
#----------------------------------------------
# Bias Card 2 (flux_fb on BC2 sets sq2_fb)
#----------------------------------------------
#echo "wb bc2 flux_fb $sq2fb0 $sq2fb1 $sq2fb2 $sq2fb3 $sq2fb4 $sq2fb5 $sq2fb6 $sq2fb7 $sq2fb8 $sq2fb9 $sq2fb10 $sq2fb11 $sq2fb12 $sq2fb13 $sq2fb14 $sq2fb15 $sq2fb16 $sq2fb17 $sq2fb18 $sq2fb19 $sq2fb20 $sq2fb21 $sq2fb22 $sq2fb23 $sq2fb24 $sq2fb25 $sq2fb26 $sq2fb27 $sq2fb28 $sq2fb29 $sq2fb30 $sq2fb31" >> $mce_script
echo "wb bc2 bias $tes_bias_bc2" >> $mce_script
                                                                                                                             
#----------------------------------------------
# Bias Card 3 (flux_fb on BC3 sets sq2_bias)
#----------------------------------------------
#echo "wb bc3 flux_fb $sq2bias0 $sq2bias1 $sq2bias2 $sq2bias3 $sq2bias4 $sq2bias5 $sq2bias6 $sq2bias7 $sq2bias8 $sq2bias9 $sq2bias10 $sq2bias11 $sq2bias12 $sq2bias13 $sq2bias14 $sq2bias15 $sq2bias16 $sq2bias17 $sq2bias18 $sq2bias19 $sq2bias20 $sq2bias21 $sq2bias22 $sq2bias23 $sq2bias24 $sq2bias25 $sq2bias26 $sq2bias27 $sq2bias28 $sq2bias29 $sq2bias30 $sq2bias31" >> $mce_script
echo "wb bc3 bias $tes_bias_bc3" >> $mce_script


#----------------------------------------------
# Bias Cards - use functional mappings!
#----------------------------------------------
if [ $config_rc1 ]; then
    echo "wra sa  fb    0 ${safb[@]: 0:8}"    >> $mce_script
    echo "wra sq2 fb    0 ${sq2fb[@]: 0:8}"   >> $mce_script
    echo "wra sq2 bias  0 ${sq2bias[@]: 0:8}" >> $mce_script
fi
if [ $config_rc2 ]; then
    echo "wra sa  fb    8 ${safb[@]: 8:8}"    >> $mce_script
    echo "wra sq2 fb    8 ${sq2fb[@]: 8:8}"   >> $mce_script
    echo "wra sq2 bias  8 ${sq2bias[@]: 8:8}" >> $mce_script
fi
if [ $config_rc3 ]; then
    echo "wra sa  fb   16 ${safb[@]:16:8}"    >> $mce_script
    echo "wra sq2 fb   16 ${sq2fb[@]:16:8}"   >> $mce_script
    echo "wra sq2 bias 16 ${sq2bias[@]:16:8}" >> $mce_script
fi
if [ $config_rc4 ]; then
    echo "wra sa  fb   24 ${safb[@]:24:8}"    >> $mce_script
    echo "wra sq2 fb   24 ${sq2fb[@]:24:8}"   >> $mce_script
    echo "wra sq2 bias 24 ${sq2bias[@]:24:8}" >> $mce_script
fi


#---------------------------------------------------------------
# Flux Jumping
#---------------------------------------------------------------
# Flux jumps occur when the 1st stage fb reaches 3/4 of the positive or negative range of the 14-bit ADC
# The flux qanta can correct the 1st stage fb by up to 6/4 of the half-range before is tirggers corrective counter-jump.  
# To see maximum variation in this test without allowing a flux-jump to get near to the point where it will cause a counter-jump, I will used a flux quanta of 5/4 the half-range of the ADC.
# [(2^14)/2]*5/4=10240
# Enable/disable flux-jumping

if [ $config_rc1 ]; then
  echo "wb rc1 en_fb_jump 0" >> $mce_script
  echo "wb rc1 flx_lp_init 1" >> $mce_script
fi
if [ $config_rc2 ]; then
  echo "wb rc2 en_fb_jump 0" >> $mce_script
  echo "wb rc2 flx_lp_init 1" >> $mce_script
fi
if [ $config_rc3 ]; then
  echo "wb rc3 en_fb_jump 0" >> $mce_script
  echo "wb rc3 flx_lp_init 1" >> $mce_script
fi
if [ $config_rc4 ]; then
  echo "wb rc4 en_fb_jump 0" >> $mce_script
  echo "wb rc4 flx_lp_init 1" >> $mce_script
fi

#END config_create.bash
