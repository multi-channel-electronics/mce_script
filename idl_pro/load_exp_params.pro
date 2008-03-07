; This file is automatically generated by mas_param!

function str_flat,a
    s = ''
    for i=0,n_elements(a)-1 do begin
        s=s+' '+strcompress(string(a(i)))
    endfor
    return,s
end

pro save_exp_params,m,filename
    spawn,'mas_param -s '+filename+' set array_width '+str_flat(m.array_width)
    spawn,'mas_param -s '+filename+' set hardware_rc '+str_flat(m.hardware_rc)
    spawn,'mas_param -s '+filename+' set hardware_sync '+str_flat(m.hardware_sync)
    spawn,'mas_param -s '+filename+' set hardware_bac '+str_flat(m.hardware_bac)
    spawn,'mas_param -s '+filename+' set sb0_select_clk '+str_flat(m.sb0_select_clk)
    spawn,'mas_param -s '+filename+' set sb0_use_dv '+str_flat(m.sb0_use_dv)
    spawn,'mas_param -s '+filename+' set sb0_use_sync '+str_flat(m.sb0_use_sync)
    spawn,'mas_param -s '+filename+' set sb1_select_clk '+str_flat(m.sb1_select_clk)
    spawn,'mas_param -s '+filename+' set sb1_use_dv '+str_flat(m.sb1_use_dv)
    spawn,'mas_param -s '+filename+' set sb1_use_sync '+str_flat(m.sb1_use_sync)
    spawn,'mas_param -s '+filename+' set default_num_rows '+str_flat(m.default_num_rows)
    spawn,'mas_param -s '+filename+' set default_sample_num '+str_flat(m.default_sample_num)
    spawn,'mas_param -s '+filename+' set default_data_mode '+str_flat(m.default_data_mode)
    spawn,'mas_param -s '+filename+' set default_servo_p '+str_flat(m.default_servo_p)
    spawn,'mas_param -s '+filename+' set default_servo_i '+str_flat(m.default_servo_i)
    spawn,'mas_param -s '+filename+' set default_servo_d '+str_flat(m.default_servo_d)
    spawn,'mas_param -s '+filename+' set default_sa_bias '+str_flat(m.default_sa_bias)
    spawn,'mas_param -s '+filename+' set default_sq2_bias '+str_flat(m.default_sq2_bias)
    spawn,'mas_param -s '+filename+' set default_sq1_bias '+str_flat(m.default_sq1_bias)
    spawn,'mas_param -s '+filename+' set sa_offset_bias_ratio '+str_flat(m.sa_offset_bias_ratio)
    spawn,'mas_param -s '+filename+' set sa_ramp_flux_start '+str_flat(m.sa_ramp_flux_start)
    spawn,'mas_param -s '+filename+' set sa_ramp_flux_count '+str_flat(m.sa_ramp_flux_count)
    spawn,'mas_param -s '+filename+' set sa_ramp_flux_step '+str_flat(m.sa_ramp_flux_step)
    spawn,'mas_param -s '+filename+' set sq2_rows '+str_flat(m.sq2_rows)
    spawn,'mas_param -s '+filename+' set sq1servo_gain '+str_flat(m.sq1servo_gain)
    spawn,'mas_param -s '+filename+' set sq2servo_gain '+str_flat(m.sq2servo_gain)
    spawn,'mas_param -s '+filename+' set sq1ramp_plot_rows '+str_flat(m.sq1ramp_plot_rows)
    spawn,'mas_param -s '+filename+' set locktest_plot_row '+str_flat(m.locktest_plot_row)
    spawn,'mas_param -s '+filename+' set locktest_pass_amplitude '+str_flat(m.locktest_pass_amplitude)
    spawn,'mas_param -s '+filename+' set sq1servo_slope '+str_flat(m.sq1servo_slope)
    spawn,'mas_param -s '+filename+' set sq2servo_slope '+str_flat(m.sq2servo_slope)
    spawn,'mas_param -s '+filename+' set tes_bias_idle '+str_flat(m.tes_bias_idle)
    spawn,'mas_param -s '+filename+' set tes_bias_normal '+str_flat(m.tes_bias_normal)
    spawn,'mas_param -s '+filename+' set tes_bias_normal_time '+str_flat(m.tes_bias_normal_time)
    spawn,'mas_param -s '+filename+' set sq2servo_safb_init '+str_flat(m.sq2servo_safb_init)
    spawn,'mas_param -s '+filename+' set sq1servo_sq2fb_init '+str_flat(m.sq1servo_sq2fb_init)
    spawn,'mas_param -s '+filename+' set config_rc '+str_flat(m.config_rc)
    spawn,'mas_param -s '+filename+' set config_sync '+str_flat(m.config_sync)
    spawn,'mas_param -s '+filename+' set config_fast_sq2 '+str_flat(m.config_fast_sq2)
    spawn,'mas_param -s '+filename+' set data_rate '+str_flat(m.data_rate)
    spawn,'mas_param -s '+filename+' set row_len '+str_flat(m.row_len)
    spawn,'mas_param -s '+filename+' set num_rows '+str_flat(m.num_rows)
    spawn,'mas_param -s '+filename+' set num_rows_reported '+str_flat(m.num_rows_reported)
    spawn,'mas_param -s '+filename+' set readout_row_index '+str_flat(m.readout_row_index)
    spawn,'mas_param -s '+filename+' set sample_dly '+str_flat(m.sample_dly)
    spawn,'mas_param -s '+filename+' set sample_num '+str_flat(m.sample_num)
    spawn,'mas_param -s '+filename+' set fb_dly '+str_flat(m.fb_dly)
    spawn,'mas_param -s '+filename+' set row_dly '+str_flat(m.row_dly)
    spawn,'mas_param -s '+filename+' set data_mode '+str_flat(m.data_mode)
    spawn,'mas_param -s '+filename+' set servo_mode '+str_flat(m.servo_mode)
    spawn,'mas_param -s '+filename+' set servo_p '+str_flat(m.servo_p)
    spawn,'mas_param -s '+filename+' set servo_i '+str_flat(m.servo_i)
    spawn,'mas_param -s '+filename+' set servo_d '+str_flat(m.servo_d)
    spawn,'mas_param -s '+filename+' set tes_bias '+str_flat(m.tes_bias)
    spawn,'mas_param -s '+filename+' set row_order '+str_flat(m.row_order)
    spawn,'mas_param -s '+filename+' set flux_quanta '+str_flat(m.flux_quanta)
    spawn,'mas_param -s '+filename+' set fb_const '+str_flat(m.fb_const)
    spawn,'mas_param -s '+filename+' set sq1_bias '+str_flat(m.sq1_bias)
    spawn,'mas_param -s '+filename+' set sq2_bias '+str_flat(m.sq2_bias)
    spawn,'mas_param -s '+filename+' set sq2_fb '+str_flat(m.sq2_fb)
    spawn,'mas_param -s '+filename+' set sq2_fb_set '+str_flat(m.sq2_fb_set)
    spawn,'mas_param -s '+filename+' set sa_bias '+str_flat(m.sa_bias)
    spawn,'mas_param -s '+filename+' set sa_fb '+str_flat(m.sa_fb)
    spawn,'mas_param -s '+filename+' set sa_offset '+str_flat(m.sa_offset)
    spawn,'mas_param -s '+filename+' set config_adc_offset_all '+str_flat(m.config_adc_offset_all)
    spawn,'mas_param -s '+filename+' set adc_offset_c '+str_flat(m.adc_offset_c)
    spawn,'mas_param -s '+filename+' set adc_offset_cr '+str_flat(m.adc_offset_cr)
end


pro load_exp_params,filename,m
    m = create_struct('_source',filename,  $
        'array_width',mas_param_int(filename,'array_width'),  $
        'hardware_rc',mas_param_int(filename,'hardware_rc'),  $
        'hardware_sync',mas_param_int(filename,'hardware_sync'),  $
        'hardware_bac',mas_param_int(filename,'hardware_bac'),  $
        'sb0_select_clk',mas_param_int(filename,'sb0_select_clk'),  $
        'sb0_use_dv',mas_param_int(filename,'sb0_use_dv'),  $
        'sb0_use_sync',mas_param_int(filename,'sb0_use_sync'),  $
        'sb1_select_clk',mas_param_int(filename,'sb1_select_clk'),  $
        'sb1_use_dv',mas_param_int(filename,'sb1_use_dv'),  $
        'sb1_use_sync',mas_param_int(filename,'sb1_use_sync'),  $
        'default_num_rows',mas_param_int(filename,'default_num_rows'),  $
        'default_sample_num',mas_param_int(filename,'default_sample_num'),  $
        'default_data_mode',mas_param_int(filename,'default_data_mode'),  $
        'default_servo_p',mas_param_int(filename,'default_servo_p'),  $
        'default_servo_i',mas_param_int(filename,'default_servo_i'),  $
        'default_servo_d',mas_param_int(filename,'default_servo_d'),  $
        'default_sa_bias',mas_param_int(filename,'default_sa_bias'),  $
        'default_sq2_bias',mas_param_int(filename,'default_sq2_bias'),  $
        'default_sq1_bias',mas_param_int(filename,'default_sq1_bias'),  $
        'sa_offset_bias_ratio',mas_param_float(filename,'sa_offset_bias_ratio'),  $
        'sa_ramp_flux_start',mas_param_int(filename,'sa_ramp_flux_start'),  $
        'sa_ramp_flux_count',mas_param_int(filename,'sa_ramp_flux_count'),  $
        'sa_ramp_flux_step',mas_param_int(filename,'sa_ramp_flux_step'),  $
        'sq2_rows',mas_param_int(filename,'sq2_rows'),  $
        'sq1servo_gain',mas_param_float(filename,'sq1servo_gain'),  $
        'sq2servo_gain',mas_param_float(filename,'sq2servo_gain'),  $
        'sq1ramp_plot_rows',mas_param_int(filename,'sq1ramp_plot_rows'),  $
        'locktest_plot_row',mas_param_int(filename,'locktest_plot_row'),  $
        'locktest_pass_amplitude',mas_param_int(filename,'locktest_pass_amplitude'),  $
        'sq1servo_slope',mas_param_int(filename,'sq1servo_slope'),  $
        'sq2servo_slope',mas_param_int(filename,'sq2servo_slope'),  $
        'tes_bias_idle',mas_param_int(filename,'tes_bias_idle'),  $
        'tes_bias_normal',mas_param_int(filename,'tes_bias_normal'),  $
        'tes_bias_normal_time',mas_param_float(filename,'tes_bias_normal_time'),  $
        'sq2servo_safb_init',mas_param_int(filename,'sq2servo_safb_init'),  $
        'sq1servo_sq2fb_init',mas_param_int(filename,'sq1servo_sq2fb_init'),  $
        'config_rc',mas_param_int(filename,'config_rc'),  $
        'config_sync',mas_param_int(filename,'config_sync'),  $
        'config_fast_sq2',mas_param_int(filename,'config_fast_sq2'),  $
        'data_rate',mas_param_int(filename,'data_rate'),  $
        'row_len',mas_param_int(filename,'row_len'),  $
        'num_rows',mas_param_int(filename,'num_rows'),  $
        'num_rows_reported',mas_param_int(filename,'num_rows_reported'),  $
        'readout_row_index',mas_param_int(filename,'readout_row_index'),  $
        'sample_dly',mas_param_int(filename,'sample_dly'),  $
        'sample_num',mas_param_int(filename,'sample_num'),  $
        'fb_dly',mas_param_int(filename,'fb_dly'),  $
        'row_dly',mas_param_int(filename,'row_dly'),  $
        'data_mode',mas_param_int(filename,'data_mode'),  $
        'servo_mode',mas_param_int(filename,'servo_mode'),  $
        'servo_p',mas_param_int(filename,'servo_p'),  $
        'servo_i',mas_param_int(filename,'servo_i'),  $
        'servo_d',mas_param_int(filename,'servo_d'),  $
        'tes_bias',mas_param_int(filename,'tes_bias'),  $
        'row_order',mas_param_int(filename,'row_order'),  $
        'flux_quanta',mas_param_int(filename,'flux_quanta'),  $
        'fb_const',mas_param_int(filename,'fb_const'),  $
        'sq1_bias',mas_param_int(filename,'sq1_bias'),  $
        'sq2_bias',mas_param_int(filename,'sq2_bias'),  $
        'sq2_fb',mas_param_int(filename,'sq2_fb'),  $
        'sq2_fb_set',mas_param_int(filename,'sq2_fb_set'),  $
        'sa_bias',mas_param_int(filename,'sa_bias'),  $
        'sa_fb',mas_param_int(filename,'sa_fb'),  $
        'sa_offset',mas_param_int(filename,'sa_offset'),  $
        'config_adc_offset_all',mas_param_int(filename,'config_adc_offset_all'),  $
        'adc_offset_c',mas_param_int(filename,'adc_offset_c'),  $
        'adc_offset_cr',mas_param_int(filename,'adc_offset_cr')    )
end
