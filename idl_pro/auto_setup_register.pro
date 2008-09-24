function auto_setup_register,ctime,type,filename,numpts,note=note

if not keyword_set(note) then note='"' + getenv('MAS_LOGID') + '"' $
else note='"'+note+'"'

spawn,'acq_register ' + string(ctime) + ' ' + string(type) + ' ' + string(filename) + ' ' + $
  string(numpts) + ' ' + note,exit_status=exit_status

return,exit_status
end
