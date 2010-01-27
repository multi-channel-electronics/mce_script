function mas_rect, data, cols, rows

  s = size(data)
  nc = s[1]
  nr = s[2]
  nt = s[3]
  
  print, nc, nr
  print, cols, rows
  packing = nr*nc / (cols*rows)
  
  data1 = reform(data, cols, rows, nt*packing)
  
  return, data1

end
