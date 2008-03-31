function auto_setup_filename,rc=rc,action=action,array_id=array_id,directory=directory,ctime=ctime
;
; Abstraction layer for providing auto_setup with a data filename.
;
; Filename will be the current ctime, or the specified ctime, plus any
; arguments explicitly specified by the caller.
;
; Additional arguments are passed with optional calling arguments:
;    rc             string or integer, will appear as, e.g. '_RC2'
;    action         string, appended as suffix with '_' added automatically
;    array_id       string or integer
;    directory      string, prepended with trailing '/'
;
; Example:
;    IDL> print,auto_setup_filename(action='sq2servo',rc='2',array_id='150Ghz')
;    1206466812_150Ghz_RC2_sq2servo
;


if not keyword_set(directory) then directory = ''
if not keyword_set(ctime) then ctime = systime(1, /utc)

; ctime forms the basis for filenames
ctime_string=string(ctime,format='(i10)')
filename = ctime_string

if keyword_set(directory) then filename = directory + '/' + filename
if keyword_set(array_id) then filename = filename + '_' + string(array_id)
if keyword_set(rc) then filename = filename + '_RC'+string(rc)
if keyword_set(action) then filename = filename + '_' + string(action)

return,strcompress( filename, /remove_all )

end
