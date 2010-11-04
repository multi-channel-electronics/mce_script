pro quantum_write,d,outfile,expected=expected

  openw,lun,/get_lun,outfile
 
  yr=expected*[0.97, 1.03]
  nc = 8
  nr = n_elements(quanta[0,*])

  writeu,lun,'Means by column: '
  for c = 0,nc-1 do begin
     q = quanta[c,*] + c*0
     idx = where(q gt 0)
     writeu,lun,mean(q[idx])
  endfor
  printf,lun,''

  writeu,lun,'Rows by column: '
  for c = 0,nc-1 do begin
     writeu,lun,q
  endfor
  printf,lun,''

  close,lun
  free_lun,lun

end
