pro auto_setup_mask_dead, mask, filespec=filespec, single_file=single_file, accumulate=accumulate

; All mask files must use the same dimensions! This is not checked.
; The output array is row dominant, i.e. mask[row,col] is your flag.

  if not keyword_set(cumulative) then begin
     n_rows = 41
     n_cols = 32
     mask = intarr(n_rows, n_cols)
  endif else begin
     s = size(mask)
     n_cols = s[1]
     n_rows = s[2]
  endelse

  if keyword_set(single_file) then filenames = [single_file] $
  else filenames = file_search(filespec)

  n_files = n_elements(filenames)
  for fi = 0, n_files-1 do begin
     filename = filenames[fi]
     load_mask_params,filename,this_mask
     
     this_mask_r = reform(this_mask.mask, [this_mask.n_rows, this_mask.n_cols])
     mask = mask or this_mask_r
  endfor

end
