function auto_setup_userword,rc

; Make sure userword contains data_mode and array_id
spawn, 'update_userword ' + string(rc), exit_status=exit_status

return, exit_status

end
