function auto_setup_current_data,base=base,datefile=datefile, $
                                 analysis=analysis,data=data
  ; Returns structure with members:
  ;   name      the label for the directory
  ;   folder    the directory into which to put data
  ;   analysis  the directoyr into which to put plots

  if not keyword_set(base) then base = '/data/cryo'
  if not keyword_set(analysis) then analysis = 'analysis'
  if not keyword_set(data) then data = ''
  if not keyword_set(datefile) then datefile = base + '/current_data_name'

  openr, /get_lun, lun, datefile
  current_data = ''
  readf, lun, current_data
  free_lun, lun
  
  data_dir = base + '/' + current_data + '/' + data + '/'
  analysis_dir = base + '/' + current_data + '/' + analysis + '/'

  return, {name: current_data, folder: data_dir, analysis: analysis_dir}

end
