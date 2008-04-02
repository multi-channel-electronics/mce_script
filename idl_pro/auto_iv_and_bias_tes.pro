pro auto_iv_and_bias_tes,change_bias=change_bias

!path='/home/mce/idl_pro:'+!path

;print,scheduler_note

if keyword_set(change_bias) then change_bias=change_bias else change_bias=1
if change_bias ne 0 then change_bias=1

;!MFH
load_exp_params,'/data/cryo/current_data/experiment.cfg',exp_config
;rc=['1','2','3','4']

current_data = ''
openr, 3, '/data/cryo/current_data_name'
readf, 3, current_data
close, 3

config_file = 'config_mce_auto_setup_'+current_data
spawn,'/data/cryo/current_data/'+config_file
;for i=0,n_elements(rc)-1 do begin
for i=0,3 do begin
    if exp_config.config_rc(i) then begin
        rc = string(strcompress(i+1,/REMOVE_ALL))
        auto_setup_command,'wb rc'+rc+' en_fb_jump 1'
;        auto_setup_command,'wb rc'+rc+' en_fb_jump 0'
        auto_setup_command,'wb rc'+rc+' data_mode 4'
    endif
endfor

;!MFH
if total(exp_config.config_rc) eq 4 then begin 
	rc='s'
        iv_filename = auto_setup_filename(rc=rc,action='iv') 
        spawn, 'ramp_tes_bias '+iv_filename+' '+rc 
        if change_bias eq 1 then $ 
          iv_anal_mce_ar1_bias, /biasfile, /plotgen $   ;, /filtered $ 
        else iv_anal_mce_ar1_bias, /plotgen 
        spawn, '/data/cryo/tes_bias_recommended' 
endif else begin
   for i=0,3 do begin
     if exp_config.config_rc(i) then begin
        rc = string(strcompress(i+1,/REMOVE_ALL))
        iv_filename = auto_setup_filename(rc=rc,action='iv')
        spawn, 'ramp_tes_bias '+iv_filename+' '+rc
        if change_bias eq 1 then $
          iv_anal_mce_ar1_bias, /biasfile, /plotgen $	;, /filtered $
        else iv_anal_mce_ar1_bias, /plotgen
        spawn, '/data/cryo/tes_bias_recommended'
     endif
   endfor
endelse

;for i=0,n_elements(rc)-1 do begin
for i=0,3 do begin
    if exp_config.config_rc(i) then begin
        rc = string(strcompress(i+1,/REMOVE_ALL))
        auto_setup_command,'wb rc'+rc+' en_fb_jump 0'
        auto_setup_command,'wb rc'+rc+' data_mode 2'
    endif
endfor

exit,status=49

end
