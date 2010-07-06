function raw_to_shift, filename, frame_info=frame_info
; Translate a rawraw (straight from 
;


d = mas_data(filename, frame_info=frame_info)
n_cols=frame_info.n_columns
n_rows=frame_info.n_rows
n_frames=frame_info.n_frames

de = fltarr(n_cols, n_rows*n_frames)

for c = 0,n_cols-1 do begin 
    src_c = c
    for f = 0,n_frames-1 do begin
        de[c, f*n_rows + lindgen(n_rows)] = d[src_c,*,f]
        src_c = (src_c + 5) mod n_cols
    endfor        
end

return,de

end

