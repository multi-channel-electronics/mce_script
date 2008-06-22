; vphi_limits is used to compute min/max/period of vphi curves

function vphi_limits, sq1, col=col,all_cols=all_cols

s = size(sq1.y)
n_col = s[1]
n_pt  = s[2]

lo = n_pt / 4
hi = n_pt - 1
z = fltarr(hi-lo+1)

if keyword_set(all_cols) then begin
    s_max = fltarr(n_col)
    s_min = s_max
    s_per = s_min

    for c=0,n_col-1 do begin
        z = reform(sq1.y[c,lo:hi])
        s_max[c] = max(z)
        s_min[c] = min(z)
        s_per[c] = vphi_period(z, fit_width=n_pt/8)
        if s_per[c] ne -1 then s_per[c] = s_per[c] * (sq1.x[1]-sq1.x[0])
    endfor
    
endif else begin
    z = reform(sq1.y[col,lo:hi])
    s_max = max(z)
    s_min = min(z)
    s_per = vphi_period(z, fit_width=n_pt/8)
    if s_per ne -1 then s_per = s_per * (sq1.x[1]-sq1.x[0])

endelse


return, create_struct('max',s_max,'min',s_min,'per',s_per)

end


;
; Load sq1 servo data for a column, and plot it agains sq2 curve.
;
; First argument is full sq2servo filename.  Second argument is base
; of sq1servo files; _row#_sq1servo will be appended.  To override the
; per-file sq1servo runfile, pass sq1runfile=...
;

pro place_sq1,sq2file,sq1base,column,sq1runfile=sq1runfile


;tune='/data/cryo/current_data/1214033521/'
;sq2file=tune+'1214033645_RC2_sq2servo'
;sq1base=tune+'1214033655_RC2_row'

;sq2file = '/home/mhasse/1212381965/1212382189_RC1_sq2servo'
;sq1file = '/home/mhasse/1212381965/1212382195_RC1_sq1servo'

sq1superfix='_row'
sq1suffix='_sq1servo'

; Load and analyze sq2 vphi

sq2 = read_bias_data(sq2file, npts=npts_sq2, rescale=0.001)
mm2 = vphi_limits(sq2,/all_cols)

s = 10
c = column
n_rows = 33

!p.multi = [0,2,2]

x = sq2.x
y = smooth(sq2.y[c,*],s)
lo = x[0]/4
hi = x[npts_sq2-1]

plot,x,y,title='Servo output'
plot,x,smooth(sq2.err[c,*],s),title='Error signal'

range = mm2.max[c] - mm2.min[c]


headspace = range
delta = headspace / n_rows

plot,x,y, xr=[lo,hi], yr=[mm2.min[c]-range*0.1, mm2.max[c]+headspace]

print,'     row       centre   pk-pk'
for r = 0, n_rows-1 do begin

    sq1file = strcompress(sq1base+sq1superfix+string(r)+sq1suffix,/remove_all)

    sq1 = read_bias_data(sq1file, npts=npts_sq1, rescale=0.001,runfile=sq1runfile)
    mm1 = vphi_limits(sq1,col=c)
    y = mm2.max[c] + r*delta
    for x =-3,3 do begin
        color = 255*65536
        if x eq 0 then color=255
        oplot,[mm1.min, mm1.max]+mm2.per[c]*x,[y,y], $
          color=color
        oplot,(mm1.min+mm1.max)/2*[1,1]+mm2.per[c]*x,[y,y]
    endfor

;    ;Overplot the sq1 vphi...
;    y_scale = (mm2.max[c]-mm2.min[c])*(sq1.x/16000)+(mm2.max[c]+mm2.min[c])/2
;    oplot,sq1.y[c,*]/1000,y_scale/1000
;    oplot,mm1.min[c]*[1,1]/1000,[1e5,-1e5]
;    oplot,mm1.max[c]*[1,1]/1000,[1e5,-1e5]


    x = sq1.x
;    plot,x,smooth(sq1.y[c,*],1)

    print,r,(mm1.max+mm1.min)/2, mm1.max-mm1.min
;    print,'Row'+string(r)+':  center ='+string((mm1.max+mm1.min)/2)+ $
;      '  width = '+string((mm1.max-mm1.min))
    ;print,mm2.per[c]
    ;print,mm1.max,mm1.min,mm1.per[c]
    
    wait,1
endfor

end
