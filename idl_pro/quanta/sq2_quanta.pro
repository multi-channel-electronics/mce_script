function sq2_quanta,ctime=ctime,tuning_folder=tuning_folder,filename=filename,expected=expected, $
                    plots_on=plots_on
  
  if not keyword_set(expected) then expected = 30000

  if keyword_set(filename) then begin
     files = [filename]
  endif else begin
     if not keyword_set(tuning_folder) then $
        tuning_folder = '/data/cryo/current_data/'+ctime
     files = file_search(tuning_folder + '/*sq2servo')
     files = files[sort(files)]
  endelse

  for i = 0,n_elements(files) - 1 do begin
     print,files[i]
     q = measure_quanta(files[i], expected=expected, /servo, plots_on=plots_on, /quiet)
     q = q[*,0]
     print, long(q)
  endfor
  return, q
end
