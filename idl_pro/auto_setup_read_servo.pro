function auto_setup_read_servo,filename,biasfile=biasfile,runfile=runfile, $
                               start=start,count=count,step=step, $
                               bias_start=bias_start,bias_count=bias_count,bias_step=bias_step

  if not keyword_set(runfile) then $
     runfile = filename + '.run'

  if not keyword_set(biasfile) then $
     biasfile = filename + '.bias'
  
  if not keyword_set(start) then begin
     ; Load ramp params from runfile?
     rf = mas_runfile(runfile)
     loop_params_b = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
     loop_params_f = mas_runparam(rf,'par_ramp','par_step loop2 par1',/long)
     
     bias_start = loop_params_b[0]
     bias_step = loop_params_b[1]
     bias_count = loop_params_b[2]
     
     start = loop_params_f[0]
     step = loop_params_f[1]
     count = loop_params_f[2]
  endif

  ncol = 8
  npts = count * bias_count
  er1 = fltarr(ncol, npts)
  fb1 = fltarr(ncol, npts)
  values = fltarr(ncol*2)

  ; Read servo output from .bias file
  openr,lun,/get_lun,biasfile
  line = ''
  readf,lun, line
  for i=0, npts-1 do begin
     readf,lun, line
     data=strmid(line, 0)
     reads,data, values
     er1[*,i]=values[0:7]
     fb1[*,i]=values[8:15]
  endfor
  free_lun,lun

  return, { error: er1, feedback: fb1, $
            start: start, step: step, count: count }
end
