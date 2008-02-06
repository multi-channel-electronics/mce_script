function mas_param_float,filename,key
    spawn,'mas_param -s '+filename+' get '+key,r,exit_status=status
    if status ne 0 then begin
        print,'Failed to load parameter '+key
        return,0
    endif
    for i=0,n_elements(r) - 1 do begin
        if keyword_set(x) then $
          x = [ x, float(strsplit(r(i),/extract)) ] $
        else $
          x = float(strsplit(r(i),/extract))
    endfor
    return,x    
end
