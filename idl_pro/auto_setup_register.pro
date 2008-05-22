function auto_setup_register,ctime,type,filename,numpts,note=note

;; Put your acquisition registration code here!

; if not keyword_set(note) then note='""' $
; else note='"'+note+'"'

; spawn,'acq_register ' + string(ctime) + ' ' + string(type) + ' ' + string(filename) + ' ' + $
;   string(numpts) + ' ' + note,exit_status=exit_status

; return,exit_status

return,0

end
