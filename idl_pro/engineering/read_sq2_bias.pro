pro read_sq2_bias,column,sq2pattern,biases

n_bias = n_elements(biases)

ff = file_search(sq2pattern+strtrim(biases[0],2)+'_sq2servo.run')
sq2file = ff[0]
rf = mas_runfile(sq2file)
lp = long(strsplit(mas_runparam(rf, 'par_ramp', 'par_step loop2 par1'),/extract))

n_fb = lp[2]
fbs = lp[0] + lp[1]*findgen(n_fb)

; Chop chop
fb_start = n_fb*0.25
fb_stop  = n_fb-1
fb_count = fb_stop-fb_start+1
fb_indices = fb_start + indgen(fb_count)

y = fltarr(fb_count*n_bias)

; I dunno, 2 rows?
;!p.multi = [0,1,2]

row = 0

for b = 0,n_bias-1 do begin
    ff = file_search(sq2pattern+strtrim(biases[b],2)+'_sq2servo')
    sq2file = ff[0]
    sq2 = read_bias_data(sq2file,rescale=0.001)
    y[(b*fb_count):(b+1)*fb_count-1] = sq2.y[column,fb_indices]

endfor

ylo = min(y)
yhi = max(y)

plot,y
for b=0,n_bias-1 do begin
    oplot,[1,1]*(fb_count*(b+1)), [-1,1]*1e6,color=255
    xyouts,fb_count*(b+1), ylo+100, string(biases[b]), alignment=1.
endfor

end

