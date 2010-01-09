; unpack_rectangle.pro
;
; For simple rectangle mode data files having num_cols_reported = 8.
;
; Given an array of frame data and a mas_runfile object, unpack the
; data according to the information in the runfile block.
;

function unpack_rectangle, data, rf

ds = size(data)
nc = ds[1]
nr_cc = ds[2]
nt_cc = ds[3]

nr_rc = mas_runparam(rf, 'HEADER', 'RB rc1 num_rows_reported', /long)
nc_rc = mas_runparam(rf, 'HEADER', 'RB rc1 num_cols_reported', /long)
if nc_rc ne 8 then $
  print,'we can not handle num_cols_reported!=8'
packing = nr_cc / nr_rc

return,reform(data, nc, nr_rc, packing*nt_cc)
end
