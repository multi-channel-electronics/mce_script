pro quantum_plot,quanta,expected=expected

  yr=expected*[0.97, 1.03]
  nc = 8
  nr = n_elements(quanta[0,*])

  plot,quanta[0,*],yr=yr,/nodata

  for c = 0,nc-1 do begin
     q = quanta[c,*] + c*0
     idx = where(q gt 0)
     oplot,idx, q[idx]
     print,mean(q[idx]),sqrt(mean(q[idx]^2)-(mean(q[idx]))^2)
  endfor

  print,'Median refined:'
  for c = 0,nc-1 do begin
     q = quanta[c,*] + c*0
     m = median(q)
     idx = where(abs((q-m)/m) lt 0.02)
     if idx[0] ne -1 then begin
         oplot,idx, q[idx],color=255
         print,mean(q[idx]),sqrt(mean(q[idx]^2)-(mean(q[idx]))^2)
     endif else $
       print,'No solution'
  endfor

  plot,findgen(nc+1)-1, quanta[*,0],yr=yr,/nodata
  for c = 0,nc-1 do begin
     q = quanta[c,*] + c*0
     idx = where(q gt expected/2)
     if idx[0] ne -1 then begin
         oplot,c + intarr(nr),q[idx],psym=2
         xyouts,c,mean(q[idx]),strcompress(string(n_elements(idx)))
     endif else $
       print,'No solution'
  endfor
  
end
