function auto_setup_userword,rc

; Make sure userword contains data_mode, array_id, ctime
spawn, 'mce_update_userword ' + string(rc), exit_status=exit_status

return, exit_status

end
