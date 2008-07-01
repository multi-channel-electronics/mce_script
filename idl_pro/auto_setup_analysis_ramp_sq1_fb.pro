function auto_setup_analysis_ramp_sq1_fb, file_name,plot_file=plot_file,rows=rows

;  Jun. 28, 2008 - Teased analysis section out of auto_setup_ramp_sq1_fb_plot.pro
;
; Previously:
;  Aug. 21, 2006 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from ramp_sq1_fb_plot.pro 
;  Feb. 18, 2007 M. Niemack added new_adc_offset calculation method 
;		to find largest region with non-zero slope

; Given a data file that is the output of the ramp_sq1_fb script,
; this script analyses the vphi curves, and determines:
;    - ideal adc_offset for each channel
;    - peak-to-peak, lock-range, lock-slopes of each V-phi.
;    - presence of multiple locking points
;
; Optionally the script produces post-script plots and runfile blocks.

;common ramp_sq1_var, new_adc_offset, squid_p2p, squid_lockrange, squid_lockslope, squid_multilock
;common ramp_sq1_var

rf = mas_runfile(file_name+'.run')
loop_params = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
numrows = mas_runparam(rf, 'HEADER', 'RB cc num_rows_reported')

; Default to all rows
if not keyword_set(rows) then rows = indgen(numrows)


v_factor = 1.
v_units = ' (AD Units/1000)'
i_factor = 1.
i_units = ' (AD Units/1000)'

; Set up plotting
if keyword_set(plot_file) then begin
    set_plot, 'ps'
    device, filename= plot_file, /landscape
    !p.multi=[0,2,4]            ;Multiple plot parameters.
    !p.region=[0,0,0,0]         ;Plot region.
endif

;readin=auto_setup_read_2d_ramp_s1(file_name,numrows=numrows)  ;Read in file
data = mas_data(file_name)
; readin.data [ samp, bias, col, row ]

; Read labels, loop sizes, etc.

;!horiz_label=readin.labels[1]
;!vert_label = readin.labels[1]
;!card = readin.labels[0]

;!n_fb = readin.specs[0]
;!fb_start = readin.specs[1]
;!fb_step =  readin.specs[2]
loop_params = mas_runparam(rf, 'par_ramp', 'loop_list')
if n_elements(strsplit(loop_params,/extract)) eq 2 then begin
    bias_params = mas_runparam(rf, 'par_ramp', 'par_step loop1 par1', /long)
    bias_start = bias_params[0]
    bias_step = bias_params[1]
    n_bias = bias_params[2]
   
    fb_params = mas_runparam(rf, 'par_ramp', 'par_step loop2 par1', /long)
endif else begin
    bias_start = -1
    bias_step = 0
    n_bias = 1

    fb_params = mas_runparam(rf, 'par_ramp', 'par_step loop1 par1', /long)
endelse

fb_start = fb_params[0]
fb_step = fb_params[1]
n_fb = fb_params[2]

;!n_bias = readin.specs[3]
;!bias_start = readin.specs[4]
;!bias_step =  readin.specs[5]

s1_bias=reform(fltarr(n_bias))
for m=0, n_bias-1 do begin
	s1_bias(m) = bias_start + m* bias_step 
endfor

s1_fb=reform(fltarr(n_fb))
for m=0, n_fb-1 do begin
	s1_fb(m) = fb_start + m* fb_step 
endfor

a=0
b=399

s1b=''

sizdat=size(data)
n_cols = sizdat[1]
n_rows = sizdat[2]
n_samp = sizdat[3]

new_adc_offset=lonarr(n_cols, n_rows)
squid_p2p=lonarr(n_cols,n_rows)
squid_lockrange=lonarr(n_cols,n_rows)
squid_lockslope=fltarr(n_cols,n_rows,2)
slope_pnts = 10		;Number of points to fit to find the slope at zero crossing points.
squid_multilock=intarr(n_cols,n_rows)


; Processing and plotting.  Sheesh!

for j=0,n_bias-1 do begin
        for kr=0,n_elements(rows)-1 do begin
            k = rows(kr)
	    for i=0, 7 do begin
                ; Work with data from this bias / row / column
                this_data = reform(data[i,k,j*n_fb:(j+1)*n_fb-1])

	        label = 'SA Channel ' + string(i, format='(f3.0)')	
	        plot, s1_fb[a:b]/1000., this_data[a:b]/1000., xtitle="SQ1_FB"+i_units, ytitle="Voltage"+v_units,$
	        charsize=1.2, xstyle=1, /ynozero,$
	        xrange=[min(s1_fb)/1000., max(s1_fb)/1000.], title= label;, yr=[-30,30]
		;Select adc offsets to be in the largest gap between all slope=0 regions in the v-phi curve
		smnum = 10
		smdat = smooth(this_data[*],smnum)

		smdat_der = smdat - shift(smdat,-1);(smdat,0,-1)
		zero_slope = intarr(b+1)
		zerocross = intarr(b+1)
		for l=a+smnum,b-1-smnum do begin
			if smdat_der(l) le 0 and smdat_der(l+1) gt 0 then zero_slope(l)=1
			if smdat_der(l) ge 0 and smdat_der(l+1) lt 0 then zero_slope(l)=1
			if smdat(l) ge 0 and smdat(l+1) lt 0 then zerocross(l) = -1
			if smdat(l) le 0 and smdat(l+1) gt 0 then zerocross(l) = 1
		endfor
		low_sl = where(zero_slope eq 1)
		if low_sl(0) ne -1 then begin
	        	oplot, s1_fb[a:b]/1000., smdat/1000., linestyle=1
			oplot, s1_fb[low_sl(*)]/1000.,smdat(low_sl(*))/1000.,psym=1
			oplot, [s1_fb(a),s1_fb(b)],[0.,0.],linestyle=2
			nls = n_elements(low_sl)
			if nls gt 1 then begin
				low_sl_order = sort(smdat(low_sl))
				low_sl_diff = abs(smdat(low_sl(low_sl_order(0:nls-2)))-smdat(low_sl(low_sl_order(1:nls-1))))
				select = where(low_sl_diff eq max(low_sl_diff))
;				if i eq 1 then stop
;				if select(0) eq -1 or n_elements(select) gt 1 then begin
				if select(0) eq -1 then begin
;					print, 'You have adc_offset selection problems on Column '$
;						+strtrim(i,1)+' Row '+strtrim(k)+'.  Take a deep breath.'
                	                new_adc_offset(i,k)=0.
		                        squid_lockrange(i,k)=0.
					squid_lockslope(i,k,*)=0.
					squid_multilock(i,k)=0.
				endif else begin
					new_adc_offset(i,k)=(smdat(low_sl(low_sl_order(select(0))))+smdat(low_sl(low_sl_order(select(0)+1))))/2

		; Simplified version of adc_offset selection just picks the middle of the total amplitude
;					new_adc_offset(i,k)=(max(smdat)+min(smdat))/2.
					squid_lockrange(i,k)=abs(smdat(low_sl(low_sl_order(select(0))))-smdat(low_sl(low_sl_order(select(0)+1))))
					; Fit a line to the slope near the lockpoint to store an estimate of the slope data.
;					if i eq 1 then stop
					dnsl = where(zerocross eq -1)
					upsl = where(zerocross eq 1)
					if dnsl(0) ne -1 then begin
						downfit = linfit(s1_fb(dnsl(0)-slope_pnts/2:dnsl(0)+slope_pnts/2),this_data[dnsl(0)-slope_pnts/2:dnsl(0)+slope_pnts/2])
 						squid_lockslope(i,k,0)=downfit(1)
						oplot, [-8,8],[downfit(0)/1000.-8*downfit(1),downfit(0)/1000.+8*downfit(1)], linestyle=1
					endif
					if upsl(0) ne -1 then begin
						upfit = linfit(s1_fb(upsl(0)-slope_pnts/2:upsl(0)+slope_pnts/2),this_data[upsl(0)-slope_pnts/2:upsl(0)+slope_pnts/2])
 						squid_lockslope(i,k,1)=upfit(1)
						oplot, [-8,8],[upfit(0)/1000.-8*upfit(1),upfit(0)/1000.+8*upfit(1)], linestyle=1
					endif
					if n_elements(dnsl)+n_elements(upsl) gt 5 then squid_multilock(i,k) = n_elements(dnsl)+n_elements(upsl)
				endelse
			endif else begin
        	                new_adc_offset(i,k)=0.
				squid_lockrange(i,k)=0.
                                squid_lockslope(i,k,*)=0.
                                squid_multilock(i,k)=0.
	                endelse
		endif else begin
			new_adc_offset(i,k)=0.
			squid_lockrange(i,k)=0.
                        squid_lockslope(i,k,*)=0.
                        squid_multilock(i,k)=0.
		endelse
		squid_p2p(i,k)=abs(max(smdat)-min(smdat))
	; Simplified version of adc_offset selection just picks the middle of the total amplitude
;		new_adc_offset(i,k)=(max(smdat)+min(smdat))/2  ; Note: Old method of selection used smnum=5
	    endfor  ; end of plotting loop in 8 columns.
	    label_row='row #'+string(k) 
	    xyouts, .1, 1.0, file_name + ' , '+ label_row , charsize=1.2, /normal
;	    xyouts, 0.7, 1.0, 'sq1 bias = ' + s1b , charsize=1.2, /normal
;	    xyouts, 0.4, 1.1, label_row , charsize=1.2, /normal
	endfor  ; End of loop in 33 rows.
endfor

if keyword_set(plot_file) then begin
    device, /close              ;close ps
endif

result = { adc_offset:new_adc_offset,p2p:squid_p2p,lockrange:squid_lockrange, $
           lockslope:squid_lockslope,multilock:squid_multilock }

return, result

end
