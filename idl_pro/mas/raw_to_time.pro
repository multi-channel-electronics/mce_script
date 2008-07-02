function raw_to_time, filename, frame_info=frame_info
; Translate a rawraw (straight from 
;


d = mas_data(filename, frame_info=frame_info)
n_cols=frame_info.n_columns
n_rows=frame_info.n_rows
n_frames=frame_info.n_frames

de = fltarr(n_cols, n_rows*n_frames)

for f = 0,n_frames-1 do begin
    de[*, f*n_rows + lindgen(n_rows)] = d[*,*,f]
end

return,de

end

