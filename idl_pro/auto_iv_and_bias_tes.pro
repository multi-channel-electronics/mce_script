pro auto_iv_and_bias_tes,change_bias=change_bias

!path='/home/mce/idl_pro:'+!path

;print,scheduler_note

if keyword_set(change_bias) then change_bias=change_bias else change_bias=1
if change_bias ne 0 then change_bias=1

; Only analyze readout cards specified in experiment.cfg 
load_exp_params,'/data/cryo/current_data/experiment.cfg',exp_config
;rc=['1','2','3','4']

current_data = ''
openr, 3, '/data/cryo/current_data_name'
readf, 3, current_data
close, 3

data_dir=getenv('MAS_DATA')

config_file = 'config_mce_auto_setup_'+current_data
spawn,'/data/cryo/current_data/'+config_file
;for i=0,n_elements(rc)-1 do begin
for i=0,3 do begin
    if exp_config.config_rc(i) then begin
        rc = string(strcompress(i+1,/REMOVE_ALL))
        auto_setup_command,'wb rc'+rc+' en_fb_jump 1'
;        auto_setup_command,'wb rc'+rc+' en_fb_jump 0'
        auto_setup_command,'wb rc'+rc+' data_mode '+string(exp_config.iv_data_mode[0])
    endif
endfor

;!MFH
if total(exp_config.config_rc) eq 4 then begin 
	rc='s'
        iv_filename = auto_setup_filename(rc=rc,action='iv',acq_id=acq_id)
        ; Prepend the directory to iv_filename, since ramp_tes_bias does.
        err = auto_setup_register(acq_id, 'iv', data_dir+iv_filename, $
                                  exp_config.ramp_tes_count, note=getenv('MAS_LOGID'))
        spawn, 'ramp_tes_bias '+iv_filename+' '+rc 
        if change_bias eq 1 then $ 
          iv_analysis, /biasfile, /plotgen, /filtered, /post_plot $ 
        else iv_analysis, /plotgen, /filtered, /post_plot 
        spawn, '/data/cryo/tes_bias_recommended' 
endif else begin
   for i=0,3 do begin
     if exp_config.config_rc(i) then begin
        rc = string(strcompress(i+1,/REMOVE_ALL))
        iv_filename = auto_setup_filename(rc=rc,action='iv',acq_id=acq_id)
        ; Prepend the directory to iv_filename, since ramp_tes_bias does.
        err = auto_setup_register(acq_id, 'iv', data_dir+iv_filename, $
                                  exp_config.ramp_tes_count, note=getenv('MAS_LOGID'))
        spawn, 'ramp_tes_bias '+iv_filename+' '+rc
        if change_bias eq 1 then $
          iv_analysis, /biasfile, /plotgen, /filtered, /post_plot $
        else iv_analysis, /plotgen, /filtered, /post_plot
        spawn, '/data/cryo/tes_bias_recommended'
     endif
   endfor
endelse

; Restore flux-jumping and data mode from config file:
;for i=0,n_elements(rc)-1 do begin
for i=0,3 do begin
    if exp_config.config_rc(i) then begin
        rc = string(strcompress(i+1,/REMOVE_ALL))
        auto_setup_command,'wb rc'+rc+' en_fb_jump '+ $
                           string(exp_config.flux_jumping)
        auto_setup_command,'wb rc'+rc+' data_mode ' + $
                           string(exp_config.data_mode)
        auto_setup_command,'wb rc'+rc+' flx_lp_init 1'
    endif
endfor

exit,status=49

end
