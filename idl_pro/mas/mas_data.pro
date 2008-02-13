; mas_data - load mce frame data into idl
;
; Matthew Hasselfield - adapted from auto_setup_frametest_plot
;

function mas_data, filename, COL=column, ROW=row, RC=rc,frame_range=frame_range, $
                   structure_only=structure_only,data_mode=data_mode,frame_info=frame_info, $
                   data2=data2,no_split=no_split,split_bits=split_bits

; Usage:
;   mas_data, filename
;
; Keywords:
;   col=col        unimplemented!
;   row=row        unimplemented!
;   rc=rc          unimplemented!
;   frame_range    start and end indices of frames to load. Defaults to all data in file.
;   structure_only does not load data, but does fill frame_info frame the first frame header.
;   data_mode      if specified, can be used to force a default bit splitting
;   frame_info     destination structure for frame data file information
;   data2          destination for upper bits of data in mixed data modes
;


fn_name='mas_data.pro'

; List of header version numbers that we understand
allowed_headers = [6]

; no bit split by default...
if not keyword_set(split_bits) then split_bits = 0

if keyword_set(data_mode) then begin
    if data_mode eq 2 then split_bits = 14
endif

;
; Determine the header version using initial words
;

prelim_count = 44   ; Might as well read a complete header, for now.
prelim_data = lonarr(prelim_count)
openr,data_lun,filename,/get_lun
data_stat = fstat(data_lun)
readu,data_lun,prelim_data
free_lun,data_lun

; Assert header is v6
if prelim_data(6) ne 6 then begin
    print,fn_name + ': header version is not 6, and that confuses me.'
    return,-1
endif

; Load other header information
header = prelim_data

rc_bits = (header(0) / 2^10) AND 15
rc_present = [(rc_bits    ) AND 1, $
              (rc_bits / 2) AND 1, $
              (rc_bits / 4) AND 1, $
              (rc_bits / 8) AND 1 ]
rc_count = total(rc_present)

frame_info = create_struct( $
                            'version',     header(6), $
                            'row_len',     header(2), $
                            'num_rows_rep',header(3), $
                            'data_rate',   header(4), $
                            'num_rows',    header(9), $
                            'rc_present',  rc_present, $
                            'rc_count',    rc_count, $
                            'n_frames',    0, $ ; place holder
                            'n_columns',   8*rc_count, $
                            'n_rows',      header(3), $
                            'frame_size',  0, $ ; place holder
                            'data_size',   0, $ ; place holder
                            'footer_size',  1, $
                            'data_offset', 43 $
)

;Calculate frame size and count, assuming 8 columns per card...
frame_info.data_size = frame_info.n_columns*frame_info.n_rows
frame_info.frame_size = frame_info.data_offset + frame_info.footer_size + frame_info.data_size
frame_info.n_frames = fix(data_stat.size / 4 / frame_info.frame_size)

if keyword_set(structure_only) then return,0

; Set or check frame range
if not keyword_set(frame_range) then frame_range = [0, frame_info.n_frames-1]
if frame_range(0) lt 0 or frame_range(0) gt frame_info.n_frames-1 then begin
    print,fn_name+': bad frame range : ', string(frame_range)
    return,-1
endif
if frame_range(1) gt frame_info.n_frames-1 then begin
    frame_range(1) = frame_info.n_frames-1
    print,fn_name+': frame range truncated to : ', string(frame_range)
endif

; Open file and calculate seek deltas
openr,data_lun,filename,/get_lun
seek_start = long(frame_info.frame_size*frame_range(0) + frame_info.data_offset) * 4
seek_delta = long(frame_info.frame_size) * 4

; Maybe we have enough ram
data = lonarr(frame_info.n_columns, frame_info.n_rows, frame_info.n_frames, /nozero)
sample = lonarr(frame_info.n_columns, frame_info.n_rows, /nozero)

; Read
for i=0,frame_info.n_frames-1 do begin
    point_lun,data_lun, seek_start + i*seek_delta
    readu,data_lun,sample
    data(*,*,i) = sample
endfor

; Split the upper bits into data2 if split_bits is defined and no_split has not been set
if split_bits ne 0 and not keyword_set(no_split) then begin
    if keyword_set(no_split) then return,data
    data2 = data AND (2^split_bits - 1)
    data = ishft(data,-split_bits)

    d_idx = where(data2 ge 2^(split_bits - 1))
    data2(d_idx) = - (data2(d_idx) AND (2^(split_bits-1)-1))
endif

return,data

end
