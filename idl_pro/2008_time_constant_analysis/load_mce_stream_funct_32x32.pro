;Function to read in and return MCE data files in a fits-like structure format
;  Used by IV_anal_mce program

;--------------------------------------------------------------------------------------

function load_mce_stream_funct_32x32, file_in, NPTS=npts, BITPART=bitpart, numrows=numrows, IV_FILE=iv_file,binary=binary
  ;----------------------------------------------------------------------------
  header_size    = 43         ; entries in the data header
  num_col_MCE    = 32          ; columns in the output fits file
  num_row_MCE    = 33         ; default: rows written in the MCE output
  num_row_ACT    = 33         ; rows to write to the truncated fits file (41 in)
  MCE_dark_squid = 32         ; index of the dark squid
  CLK_freq       = 5.0e7      ; sampling freq in Hz (default)
  len_IV_header  = 10         ; length of IV curve information header
  ;----------------------------------------------------------------------------
if keyword_set(numrows) then num_row_MCE = numrows
if num_row_MCE lt num_row_ACT then num_row_ACT = numrows

  ;----------------------------------------------------------------------------
  ; find the full filename + path for the input data
  ; if the user specifies a date, then open that instead of the current data dir
  ;----------------------------------------------------------------------------

  full_filename_in = file_in

  ;----------------------------------------------------------------------------
  ; if the file is IV curve data then read in the header and generate bias list
  ;----------------------------------------------------------------------------
  if keyword_set(iv_file) then begin
;    readin = read_ramp_headers(full_filename_in)
    base_filename = strsplit(full_filename_in,'.iv',/extract,/regex)
    readin = read_ramp_headers(base_filename+'.bias.old')
    card = readin.labels[0]
    n_bias = readin.specs[3]
    bias_start = readin.specs[4]
    bias_step =  readin.specs[5]
    print, 'IV curve file with: ', n_bias, ' bias values from ', $
           bias_start, ' in ', bias_step, ' steps '
    tes_bias=reform(fltarr(n_bias))
    for m=0, n_bias-1 do begin
        tes_bias(m) = bias_start - m* bias_step
    endfor
    npts = n_bias
  endif

  ; if the user does not specify the number of points, then exit unless
  ; it is an IV curve, (then the number of points is in the header)
  if not keyword_set(npts) and not keyword_set(iv_file) then begin
    print, 'number of points not specified, exiting'
    exit
  endif

  ;----------------------------------------------------------------------------
  ; find the sampling frequency, number of rows
  ;----------------------------------------------------------------------------
  lun=50
  openr, lun, full_filename_in  ;, /get_lun
  IVheader = strarr(len_IV_header)
  header = lonarr(header_size)
;  if keyword_set(iv_file) then readf, lun, IVheader
  if keyword_set(binary) then begin
	readu, lun, header
  endif else begin
  	readf, lun, header
  endelse
;	print, header
  samp_freq = CLK_freq/double(33.*100.*38.);header[2]*header[3]*header[4])
  num_rows_head =33; header[3]
  print, 'sample frequency: '+string(samp_freq)
  print, 'number of rows from header: '+string(num_rows_head)
  ; if the user specifies a sampling frequency
  ;if keyword_set(f_samp) then samp_freq=f_samp

  ;----------------------------------------------------------------------------
  ; basic structure of the fits array
  ; if there are the default 41 MCE rows truncate -> 32+1 rows out
  ;----------------------------------------------------------------------------
  if not (num_rows_head eq num_row_MCE) then begin
    num_rows_in  = num_rows_head
    num_rows_out = num_rows_head
  endif else begin
    ;print, 'File is default MCE output with 41 rows, truncating'
    num_rows_in = num_row_MCE
    num_rows_out = num_row_ACT
  endelse

  fb_er_struct      = {fb: lonarr(num_col_MCE,num_rows_out), $
                       er: lonarr(num_col_MCE,num_rows_out), $
                       header: lonarr(header_size), $
                       time: 0.0}
  fb_struct         = {fb: lonarr(num_col_MCE,num_rows_out), $
                       header: lonarr(header_size), $
                       time: 0.0}

  ; make the array depending on whether the data is fb+er, fb, or in fast acq.
  if keyword_set(bitpart) then begin
    output_array = replicate(fb_er_struct, npts)
  endif else begin
    output_array = replicate(fb_struct, npts)
  endelse

  ;----------------------------------------------------------------------------
  ; read in the text file
  ;----------------------------------------------------------------------------
  print, 'reading stream '+full_filename_in
  ; blocks to read in the data from the MCE output file
  block=lonarr(num_col_MCE,num_rows_in)
  blockbincol=lonarr(num_col_MCE)
  point_lun, lun, 0
;  if keyword_set(iv_file) then readf, lun, IVheader
  m=0.
  while not eof(lun) and m lt npts do begin
    if keyword_set(binary) then begin
      readu, lun, header
      for i=0,num_rows_in-1 do begin
	readu, lun, blockbincol
  	block[*,i]=blockbincol
      endfor
      readu, lun, datum 
    endif else begin
      readf, lun, header
      readf, lun, block
      readf, lun, datum
    endelse
    ; if BITPART set, split error and feedback
    if keyword_set(bitpart) then begin
      mce_fb_data = block
      mce_er_data = block
      mce_fb_data = floor(block/2.^bitpart)
      mce_er_data = abs(floor(block-mce_fb_data*2.^bitpart))
      ; truncate the error signal if it is the default 41 rows
      if num_rows_head eq num_row_MCE then begin
        output_array[m].er[*,0:num_row_ACT-2] = mce_er_data[*,0:num_row_ACT-2]
        output_array[m].er[*,num_row_ACT-1] = mce_er_data[*,MCE_dark_squid]
      endif else begin
        ;output_array[m].er = mce_er_data
      endelse
    endif else begin
      mce_fb_data = block
    endelse
    ; for IV curve files, write the bias instead of time
    if not keyword_set(iv_file) then begin
      output_array[m].time = double(m)/double(samp_freq)
    endif else begin
      output_array[m].time = tes_bias(m)
    endelse
    ; regardless of bitpart, put the fb signal in the structure
    ; 32 channels and the dark squid (MCE channel 41)
    if num_rows_head eq num_row_MCE then begin
      output_array[m].fb[*,0:num_row_ACT-2] = mce_fb_data[*,0:num_row_ACT-2]
      output_array[m].fb[*,num_row_ACT-1] = mce_fb_data[*,MCE_dark_squid]
    endif else begin
      output_array[m].fb = mce_fb_data
    endelse
    m=m+1
  endwhile
;  free_lun, lun
  close, lun
  output_array = output_array[0:m-1]
  npts=m
  ;help, output_array, /structure

return, output_array
end
