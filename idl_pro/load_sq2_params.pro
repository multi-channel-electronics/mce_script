function str_flat,a
    s = ''
    for i=0,n_elements(a)-1 do begin
        s=s+' '+strcompress(string(a(i)))
    endfor
    return,s
end

pro save_sq2_params,m,filename
         spawn,'mas_param -f '+filename+' set fb_numrows "'+str_flat(m.fb_numrows)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan0 "'+str_flat(m.fb_chan0)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan1 "'+str_flat(m.fb_chan1)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan2 "'+str_flat(m.fb_chan2)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan3 "'+str_flat(m.fb_chan3)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan4 "'+str_flat(m.fb_chan4)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan5 "'+str_flat(m.fb_chan5)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan6 "'+str_flat(m.fb_chan6)+'"'
         spawn,'mas_param -f '+filename+' set fb_chan7 "'+str_flat(m.fb_chan7)+'"'
         spawn,'mas_param -f '+filename+' set fb_rows "'+str_flat(m.fb_rows)+'"'
end


pro load_sq2_params,filename,m
 	spawn,'mas_param -f '+filename+' get fb_numrows',r,exit_status=status
 	if status eq 0 then begin
 	  fb_numrows = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_numrows
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan0',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan0 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan0
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan1',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan1 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan1
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan2',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan2 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan2
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan3',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan3 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan3
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan4',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan4 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan4
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan5',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan5 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan5
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan6',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan6 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan6
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_chan7',r,exit_status=status
 	if status eq 0 then begin
 	  fb_chan7 = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_chan7
 	endelse
 	spawn,'mas_param -f '+filename+' get fb_rows',r,exit_status=status
 	if status eq 0 then begin
 	  fb_rows = fix(strsplit(r,/extract))
 	endif else begin
 	  print,'Failed to load parameter fb_rows
 	endelse

        m = create_struct('source',filename , 'fb_numrows',fb_numrows, 'fb_chan0',fb_chan0, 'fb_chan1',fb_chan1, 'fb_chan2',fb_chan2, 'fb_chan3',fb_chan3, 'fb_chan4',fb_chan4, 'fb_chan5',fb_chan5, 'fb_chan6',fb_chan6, 'fb_chan7',fb_chan7, 'fb_rows',fb_rows)
end

