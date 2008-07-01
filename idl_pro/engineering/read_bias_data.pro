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
lp = fix(strsplit(mas_runparam(rf,'par_ramp','par_step loop2 par1'),/extract))

x = (findgen(lp[2])*lp[1] + lp[0] ) * rescale
npts = lp[2]

n_col = 8
r1 = fltarr([n_col, npts])
y = r1
values = fltarr(16)
line = ''

openr,lun,/get_lun,biasfile
readf, lun, line

for n=0, npts-1 do begin
    readf, lun, line
    data=strmid(line, 0)
    reads,data, values
    r1[*,n]=values[0:7] * rescale
    y[*,n]=values[8:15] * rescale
endfor

free_lun,lun

sq2 = create_struct('x',x,'y',y, 'err',r1)
return,sq2

end
