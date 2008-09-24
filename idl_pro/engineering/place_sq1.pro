;
; PLACE_SQ1 - generate plots and text for the purpose of choosing the
;             best row to use for squid2 fb selection row.


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


; load_sq1servo_set is used to assemble v-phi from a set of single-row
; servos into a single data structure.

function load_sq1servo_set, sq1base

sq1suffix='_sq1servo'

; All we really care about is means and pk-pk
n_col=8
rf = mas_runfile(sq1base+'_row0'+sq1suffix+'.run')
n_row = mas_runparam(rf, 'HEADER', 'RB cc num_rows_reported')

means = fltarr([n_col, n_row])
mins = means
maxes = means
pers = means
pkpk = means

for r = 0, n_row-1 do begin

    sq1file = strcompress(sq1base+'_row'+string(r)+sq1suffix,/remove_all)

    sq1 = read_bias_data(sq1file, npts=npts_sq1, rescale=0.001,runfile=sq1runfile)
    mm1 = vphi_limits(sq1,/all_cols)
    mins[*,r] = mm1.min
    maxes[*,r] = mm1.max
    means[*,r] = (mm1.min+mm1.max)/2
    pkpk[*,r] = (mm1.max-mm1.min)/2
    pers[*,r] = mm1.per

endfor

return, create_struct('mean',means,'max',maxes,'min',mins,'per',pers,'pkpk',pkpk, $
                     'source_name',sq1base+'_row*'+sq1suffix)

end


;
; Plot sq1 servo data for 1 column.
;
; First argument is full sq2servo filename.  Second argument is data
; structure containing sq1 features (as produced by
; load_sq1servo_set).
;

pro place_sq1,sq2file,sq1_data,columns,all_cols=all_cols,plot_file=plot_file

; Load and analyze sq2 vphi

sq2 = read_bias_data(sq2file, npts=npts_sq2, rescale=0.001)
mm2 = vphi_limits(sq2,/all_cols)

s = 10
n_cols = 8
n_rows = 33

if keyword_set(all_cols) then columns = indgen(n_cols)
if keyword_set(plot_file) then begin
    set_plot, 'ps'
    device, filename=plot_file, /portrait, xsize=17., ysize=23.5, yoffset=2.
    linestyle=2
endif

x = sq2.x
lo = x[0]/4
hi = x[npts_sq2-1]

for ci = 0, n_elements(columns)-1 do begin
    c = columns[ci]

    y = smooth(sq2.y[c,*],s)

    !p.multi = [0,1,2]
    plot,x,y, xr=[lo,hi], title=sq2file+ '  Channel'+string(c), $
      xtitle='sq2_fb / 1000', ytitle='sa_fb / 1000'
    plot,x,y, xr=[lo,hi], yr=[-1,n_rows+1], /nodata, title=sq1_data.source_name, $
      xtitle='sq2_fb / 1000', ytitle='Row'

    print,'     row       centre   pk-pk'
    for r = 0, n_rows-1 do begin

        for k =-3,3 do begin
            if not keyword_set(plot_file) then begin
                color = 255*65536
                if k eq 0 then color=255
            endif else begin
                psym = 1
                if k eq 0 then psym = 6
            endelse
            
            oplot,[sq1_data.min[c,r], sq1_data.max[c,r]]+mm2.per[c]*k,[r,r], $
              color=color
            oplot,sq1_data.mean[c,r]*[1,1]+mm2.per[c]*k,[r,r],psym=psym
        endfor

        print,r,sq1_data.mean[c,r],sq1_data.pkpk[c,r]
        
    endfor

endfor


if keyword_set(plot_file) then begin
    device, /close
    set_plot,'x'
endif

end
