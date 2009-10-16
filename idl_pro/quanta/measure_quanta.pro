function measure_quanta,filename,bias_step=bias_step,bias_start=bias_start, $
                        plots_on=plots_on,expected=expected,mean_by_column=mean_by_column, $
                        quiet=quiet
;
; Returns 8 x n_rows array of v-phi periods.  Means, column by column
; after outlier removal (using 'expected') are preseent in
; 'mean_by_column'.
;


if not keyword_set (bias_step) then begin
    rf = mas_runfile(filename+'.run')
    bias_params = mas_runparam(rf, 'par_ramp', 'par_step loop1 par1',/float)
    if not keyword_set(quiet) then $
       print,bias_params
    bias_start = bias_params[0]
    bias_step = bias_params[1]
endif

d = mas_data(filename,frame_info=frame_info)

n = frame_info.n_frames
n_row = frame_info.n_rows
n_col = frame_info.n_columns

x = findgen(n)*bias_step + bias_start
p_set = fltarr([n_col, n_row])
p_set2 = p_set

for r=0,n_row-1 do begin
    for c=0,n_col-1 do begin
        y = d[c,r,*]

        p = vphi_period(y, fit_width=n/3) * bias_step
        if p lt 0 then p = 0
        p_set[c, r] = p

        ; This sine fit business doesn't work very well because
        ; there are only ~2 periods and the curve is not very siney.
;         a = fit_sine(x, y)
;         if a[0] ne -1 then $
;           p_set2[c, r] = a[2]

        if keyword_set(plots_on) then begin
            plot,x,y,xrange=[x[0], x[n-1] *2]
            oplot,x+p[0],y,color=255
        endif

        if keyword_set(expected) and abs(p - expected)/expected gt 0.1 then begin
            if not keyword_set(quiet) then $
              print,'Surprise! ',string(r)+string(c)+' is bad-amped: '+string(p)
            plot,x,y,xrange=[x[0], x[n-1] *2]
            oplot,x+p[0],y,color=255
            wait,1
        endif else $
            if not keyword_set(quiet) then $
               print,'Good:     ',string(r)+string(c)+' has period'+string(p)

    endfor
endfor

mean_by_column = fltarr(n_col)
for c=0,n_col-1 do begin
    idx = where(abs(p_set[c,*]/expected -1) lt 0.1)
    if idx[0] ne -1 then $
      mean_by_column[c] = mean(p_set[c,idx]) $
    else $
      mean_by_column[c] = -1
endfor

return, p_set

end


;
; Sine fit
;

function fit_sine, x, y

common fit_params, fit_data_x, fit_data_y

fit_data_y = y
fit_data_x = x

p0 = [1e4, 50, 2*!pi/200]
scale = [1e3,1,1]

a = amoeba(1e-6, $
  function_name='model_delta', $
  p0=p0, scale=scale)

return, a

end

function model_func, args, x

;print,args
return, args(0)*sin((x-args(1))*args(2))

end

function model_delta, args

common fit_params

return, total( (model_func(args,fit_data_x) - fit_data_y)^2 )

end
