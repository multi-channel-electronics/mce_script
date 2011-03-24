function mas_param_string,filename,key
    spawn,'mas_param -s '+filename+' get '+key,r,exit_status=status
    if status ne 0 then begin
        print,'Failed to load parameter '+key
        return,0
    endif
    ; Remove leading and trailing "s
    r = strtrim(r)
    return,strmid(r,1,strlen(r)-2)
end
