; mas_data - load mce frame data into idl
;
; Matthew Hasselfield - adapted from auto_setup_frametest_plot
;

function mas_data, filename, COL=column, ROW=row, RC=rc,frame_range=frame_range_in, $
                   structure_only=structure_only,data_mode=data_mode, $
                   frame_info=frame_info, header_data=header_data, $
                   data2=data2,no_split=no_split,no_rescale=no_rescale, $
                   no_runfile=no_runfile,runfile_name=runfile_name, $
                   no_rectangle=no_rectangle

; Usage:
;   mas_data, filename
;
; Keywords:
;   col=col        unimplemented!
;   row=row        unimplemented!
;   rc=rc          unimplemented!
;   frame_range    start and end indices of frames to load. Negative indices are   
;                  relative to end of file (so -1 is last frame).  Defaults to [0, -1].
;   structure_only does not load data, but does fill frame_info frame the first frame header.
;   data_mode      if specified, can be used to force a default bit splitting
;   frame_info     destination structure for frame data file information
;   header_data    destination structure for header time-streams
;   data2          destination for lower bits of data in mixed data modes
;   no_runfile     do not attempt to process the runfile
;   runfile_name   use this runfile name instead of filename.run
;   no_rectangle   do not unpack rectangle-mode data

fn_name='mas_data.pro'

; List of header version numbers that we understand
allowed_headers = [6]

;
; Determine the header version using initial words
;

header_size = 43L
prelim_data = lonarr(header_size)
openr,data_lun,filename,/get_lun,/swap_if_big_endian
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

rc_bits = ishft(header(0),-10)
rc_present = [     (rc_bits   ) AND 1, $
              ishft(rc_bits,-1) AND 1, $
              ishft(rc_bits,-2) AND 1, $
              ishft(rc_bits,-3) AND 1 ]
rc_count = total(rc_present)

frame_info = create_struct( $
                            'version',     header(6), $
                            'row_len',     header(2), $
                            'num_rows_rep',header(3), $
                            'data_rate',   header(4), $
                            'num_rows',    header(9), $
                            'ramp_address',header(8), $
                            'rc_present',  rc_present, $
                            'rc_count',    rc_count, $
                            'n_frames',    0L, $ ; place holder
                            'n_columns',   8L*rc_count, $
                            'n_rows',      header(3), $
                            'raw_data',    0, $
                            'data_mode',   0L, $
                            'frame_size',  0L, $ ; place holder
                            'data_size',   0L, $ ; place holder
                            'footer_size', 1L, $
                            'data_offset', header_size $
)

;Calculate frame size and count, assuming 8 columns per card...
frame_info.data_size = frame_info.n_columns*frame_info.n_rows
frame_info.frame_size = frame_info.data_offset + frame_info.footer_size + frame_info.data_size
frame_info.n_frames = long(data_stat.size / 4L / frame_info.frame_size)

if keyword_set(structure_only) then return,0

;Identify time-varying header fields of interest
header_fields = [ 'frame_ctr', 'address0_ctr', 'ramp_value', 'sync_box_num' ];
header_indices = [ 1, 5, 7, 10 ];
n_header_indices = n_elements(header_indices)

; Use our own frame_range variable so as not to change the passed value.
if not keyword_set(frame_range_in) then $
  frame_range = [0L, -1L] $
else $
  frame_range = long(frame_range_in)

; Adjust negative values relative to eof
neg_f = where(frame_range lt 0)
if neg_f[0] ne -1 then $
  frame_range[neg_f] = frame_range[neg_f] + frame_info.n_frames

; Catch bad frame ranges
if frame_range(0) lt 0 or frame_range(0) gt frame_info.n_frames-1 then begin
    print,fn_name+': bad frame range : ', string(frame_range)
    return,-1
endif

; Truncate extreme frame ranges
if frame_range(1) gt frame_info.n_frames-1 then begin
    frame_range(1) = frame_info.n_frames-1
    print,fn_name+': frame range truncated to : ', string(frame_range)
endif

; Update n_frames to reflect number of frames queried
frame_info.n_frames=frame_range(1)-frame_range(0)+1L

; Open file and calculate seek deltas
openr,data_lun,filename,/get_lun,/swap_if_big_endian
seek_start = long(frame_info.frame_size*frame_range(0)) * 4L
seek_delta = long(frame_info.frame_size) * 4L

; Maybe we have enough ram
data = lonarr(frame_info.n_columns, frame_info.n_rows, frame_info.n_frames, /nozero)
sample = lonarr(frame_info.n_columns, frame_info.n_rows, /nozero)
header_data_x = lonarr(n_elements(header_indices), frame_info.n_frames, /nozero)
header_sample = lonarr(max(header_indices) + 1)

; Read
for i=0L,frame_range[1]-frame_range[0] do begin
    if n_header_indices gt 0 then begin
        ; Read header
        point_lun,data_lun, seek_start + i*seek_delta
        readu,data_lun,header_sample
        header_data_x[*,i] = header_sample[header_indices]
    endif

    ; Read signals
    point_lun,data_lun, seek_start + frame_info.data_offset*4L + i*seek_delta 
    readu,data_lun,sample
    data(*,*,i) = sample
endfor

free_lun,data_lun

; Construct the data_header structure
if n_header_indices gt 0 then begin
    header_data = create_struct(header_fields[0], reform(header_data_x[0,*]))
    for i=1,n_header_indices-1 do $
      header_data = create_struct(header_data, header_fields[i], reform(header_data_x[i,*]))
endif

;
; Attempt to load the runfile
;
if not keyword_set(runfile_name) then $ 
  runfile_name = filename+'.run'

if not keyword_set(data_mode) and keyword_set(no_runfile) then $
  data_mode = 0

if not keyword_set(no_runfile) then begin
    rf = mas_runfile(runfile_name)
    rf_RC_list = strsplit(mas_runparam(rf,'FRAMEACQ','RC'),/extract)
    data_mode = fix(mas_runparam(rf,'HEADER','RB rc'+rf_RC_list[0]+' data_mode',error=rf_error))
endif

frame_info.data_mode = data_mode

rescale  = 1.            ; Rescaling for each field
rescale2 = 1.

; We'll put feedback into data (start/count) whenever possible.
start  = 0               ; Bit field positions and sizes
count  = 32              
start2 = 0
count2 = 0
unsigned = 0
unsigned2 = 0

if not keyword_set(no_split) then begin
    
    case data_mode of
        1: rescale = 1./2d^12
        ; 3: pass
        4: begin
            start  = 14
            count  = 18
            start2 =  0
            count2 = 14
        end
        5: begin
            start  =  8
            count  = 24
            start2 =  0 ; flux jump counter
            count2 =  8
            rescale = 2d^8
        end
        6: begin
            start  = 14
            count  = 18
            start2 =  0 ; error
            count2 = 14
            rescale = 2d^11
        end
        7: begin 
            start  = 10
            count  = 22
            start2 =  0 ; error
            count2 = 10
            rescale = 2d^7
            rescale2 = 1./2d^4
        end
        8: begin
            start  =  8
            count  = 24
            start2 =  0 ; flux jump counter
            count2 =  8
            rescale = 2d^8
        end
        9: begin
            start  =  8
            count  = 24
            start2 =  0 ; flux jump counter
            count2 =  8
            rescale = 2d^1
        end
        10: begin
            start  =  7
            count  = 25
            start2 =  0 ; flux jump counter
            count2 =  7
            rescale = 2d^3
        end
        11: begin
            start = 3
            count = 7
            unsigned = 1
            start2 = 0
            count2 = 3
            unsigned2 = 1
        end
        ; 12: pass
        else:
    endcase

endif


if count2 ne 0 then $
  data2 = extract_bitfield(data, count=count2, start=start2, unsigned=unsigned)

data1 = extract_bitfield(data, count=count, start=start, unsigned=unsigned2)

if not keyword_set(no_rescale) then begin
  data1 = data1 * rescale
  if count2 ne 0 then $
    data2 = data2 * rescale2
endif

; Reorganize raw mode data by column (output array is 2d)
if data_mode eq 3 or data_mode eq 12 then begin
    ; DM 3 has 8 columns of raw data and DM 12 has 1.
    n_col = frame_info.rc_count
    if data_mode eq 3 then $
      n_col = n_col * 8
    n_frame = frame_info.n_frames * frame_info.n_rows * frame_info.n_columns / n_col
    frame_info.n_frames = n_frame
    frame_info.n_rows = 1
    frame_info.n_columns = n_col
    
    data1 = reform(data1, frame_info.n_columns, frame_info.n_frames)
    frame_info.raw_data = 1
endif

if not keyword_set(no_rectangle) and not keyword_set(no_runfile) then begin
    ; Confirm rectangle mode
    nc = mas_runparam(rf, 'HEADER', 'RB cc num_cols_reported', error=err)
    if err ge 0 then begin
        if count2 ne 0 then $
          data2 = unpack_rectangle(data2, rf)
        return, unpack_rectangle(data1, rf)
    endif
endif

return,data1

end
