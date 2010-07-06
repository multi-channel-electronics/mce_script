function auto_setup_mask_labels,filenames,label_names,columns

n_files = n_elements(filenames)
n_cols = n_elements(columns)
n_rows = 41

for fi = 0,n_files-1 do begin
    files = file_search(filenames[fi])
    load_mask_params,files[0],this_mask
    this_mask_r = reform(this_mask.mask, [this_mask.n_rows, this_mask.n_cols])
    if fi eq 0 then $
      mask_data = intarr(n_files, n_cols, this_mask.n_rows)
    mask_data[fi, *, *] = transpose(this_mask_r[*, columns])
endfor

return, {masks: mask_data, labels: label_names, n_labels: n_files}

end
    
    
