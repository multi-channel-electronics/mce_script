pro mce_make_config,params_file=params_file,filename=filename,logfile=logfile,exit_status=exit_status,run_now=run_now

make_command = 'mce_make_config'
config_command = filename

if keyword_set(params_file) then begin
    make_command = make_command + ' ' + params_file
    if keyword_set(filename) then begin
        make_command = make_command + ' ' + filename
    endif
endif

if keyword_set(logfile) then begin
    make_command = make_command + ' >> ' + logfile
    config_command = config_command + ' >> ' + logfile
endif

; Create the config
print,'Make command: '+make_command
spawn,make_command,exit_status=status
if status ne 0 then begin
    print,'Config creation failed: ' + make_command
endif

if status ne 0 then begin
    if keyword_set(run_now) then begin
;        print,'config run suppressed!'

        spawn,config_command,exit_status=status
        if status ne 0 then begin
            print,'Config run failed: ' + config_command
        endif
    endif
endif

exit_status=status

end  ; make_config_file
