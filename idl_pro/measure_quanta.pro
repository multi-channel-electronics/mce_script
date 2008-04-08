function measure_quanta,filename,bias_step=bias_step,bias_start=bias_start, $
                        plots_on=plots_on,expected=expected

filename = '/data/cryo/20080401/1207101655/1207101807_RC1_sq1rampc'

if not keyword_set (bias_step) then begin
    rf = mas_runfile(filename+'.run')
    bias_params = float(strsplit(mas_runparam(rf, 'par_ramp', 'par_step loop1 par1'),/extract))
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

for r=0,n_row-1 do begin
    for c=0,n_col-1 do begin
        y = d[c,r,*]

        p = vphi_period(y, fit_width=n/3) * bias_step
        if p lt 0 then p = 0
        p_set[c, r] = p

        if keyword_set(plots_on) then begin
            plot,x,y,xrange=[x[0], x[n-1] *2]
            oplot,x+p[0],y,color=255
        endif

        if keyword_set(expected) and abs(p - expected)/expected gt 0.1 then begin
            print,'Surprise! ',string(r)+string(c)+' is bad-amped.'
            plot,x,y,xrange=[x[0], x[n-1] *2]
            oplot,x+p[0],y,color=255
            wait,1
        endif

    endfor
endfor

return, p_set

end
