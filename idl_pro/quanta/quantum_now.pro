pro quantum_now

  source_folder='/data/cryo/20080622/1214118276/'
  analysis_folder='analysis/'+source_folder

  fn = file_search(source_folder+'*RC4*rampc')
  expected = 7700.
  
  for f = 0,n_elements(fn)-1 do begin
     print,'Card '+string(f)
     q = measure_quanta(fn[f],expected=expected,/plots_on)
     quantum_plot,q,expected=expected
  end
  
end

