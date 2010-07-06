;
; read_bias_data - reads an sq1servo or sq2servo data set into a
;                  struct.  Output fields are x, y, and err.  The
;                  function will determine, and set, the npts
;                  keyword.  Use rescale=0.001, for example, to
;                  rescale the data by 1/1000.
;

function read_bias_data,filebase, npts=npts, rescale=rescale, runfile=runfile

biasfile = filebase+'.bias'

if not keyword_set(runfile) then $
  runfile = filebase+'.run'

if not keyword_set(rescale) then rescale = 1.

rf = mas_runfile(runfile)
lp1 = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
lp2 = mas_runparam(rf,'par_ramp','par_step loop2 par1',/long)
n_bias = lp1[2]
n_fb = lp2[2]

fb = (findgen(lp2[2])*lp2[1] + lp2[0] ) * rescale
biases = (findgen(lp1[2])*lp1[1] + lp1[0] ) * rescale

n_col = 8
r1 = fltarr([n_col, n_bias, n_fb])
y = r1
values = fltarr(16)
line = ''

openr,lun,/get_lun,biasfile
readf, lun, line

for b = 0,lp1[2]-1 do begin
    for f = 0,lp2[2]-1 do begin
        readf, lun, line
        data=strmid(line, 0)
        reads,data, values
        r1[*,b,f]=values[0:7] * rescale
        y[*,b,f]=values[8:15] * rescale
    endfor
endfor

free_lun,lun

sq2 = create_struct('fb',fb,'bias',biases,'y',y, 'err',r1, $
                   'filename',filebase)
return,sq2

end
