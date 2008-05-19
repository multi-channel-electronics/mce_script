pro quantum_now

  source_folder='rampc_1727/'
  analysis_folder='analysis/'+source_folder

  fn = file_search(getenv('MAS_DATA')+source_folder+'*rampc')
  expected = 7700.
  
  for f = 0,n_elements(fn)-1 do begin
     print,'Card '+string(f)
     q = measure_quanta(fn[f],expected=expected)
     quantum_plot,q,expected=expected
  end
  
end

