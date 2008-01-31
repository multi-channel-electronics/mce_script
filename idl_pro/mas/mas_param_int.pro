function mas_param_int,filename,key
    spawn,'mas_param -s '+filename+' get '+key,r,exit_status=status
    if status ne 0 then begin
        print,'Failed to load parameter '+key
        return,0
    endif
    for i=0,n_elements(r) - 1 do begin
        if keyword_set(x) then $
          ; type=3 is longint
          x = [ x, fix(strsplit(r(i),/extract),type=3) ] $
        else $
          x = fix(strsplit(r(i),/extract))
    endfor
    return,x
end
