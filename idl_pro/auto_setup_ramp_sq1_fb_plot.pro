pro auto_setup_ramp_sq1_fb_plot, file_name,RC=rc,interactive=interactive,numrows=numrows,rows=rows, $
                                 acq_id=acq_id


;  Aug. 21, 2006 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from ramp_sq1_fb_plot.pro 
;  Feb. 18, 2007 M. Niemack added new_adc_offset calculation method 
;		to find largest region with non-zero slope

common ramp_sq1_var

;Init
if not keyword_set(acq_id) then acq_id = 0

;Close all open files. It helps avoid some errors although shouldn't be necessary:
close,/all

;Communication:
print,''
print,'###########################################################################'
print,'#5) The fifth step is to check whether the locking is succesfull. We then #'
print,'#   run a ramp_SQ1_fb and we check the SQ1 V-phi curves.                  #'
print,'###########################################################################'
print,''

default_folder = '/data/cryo/'

default_date = 'current_data/'

date= default_date

folder= default_folder

ctime=string(file_name,format='(i10)')

logfile=ctime+'/'+ctime+'.log'

user_status = auto_setup_userword(rc)
spawn,'ramp_sq1_fb '+file_name+' '+string(rc)+ ' >> /data/cryo/current_data/'+logfile,exit_status=status13
if status13 ne 0 then begin
        print,''
        print,'######################################################################'
        print,'# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE RAMP_SQ1 CHECK SCRIPT #'
        print,'######################################################################'
        print,''
        exit,status=13
endif

cd = ''
;Set filename.
full_name=folder+date+file_name
openr, 3, '/data/cryo/current_data_name'
readf, 3,  cd
close, 3
name_label = '/data/cryo' + '/' + cd + '/' + file_name 

rf = mas_runfile(full_name+'.run')
loop_params = fix(strsplit(mas_runparam(rf,'par_ramp','par_step loop1 par1'),/extract))
reg_status = auto_setup_register(acq_id, 'tune_ramp', full_name, loop_params[2])

plot_file = folder + date + 'analysis/' +file_name + '.ps'
    
v_factor = 1.
v_units = ' (AD Units/1000)'
i_factor = 1.
i_units = ' (AD Units/1000)'

; Read in header from the data file

; Convert SA_bias to current.
vmax = 2500.  ; mV
RL  = 15000.  ; Ohms
full_scale = 65535.   ; Digital fs = 2^16 -1.
ma2uA      = 1000.    ; convert to microamperes

sa_bias = 0 * vmax * ma2uA  / ( RL* full_scale)
    
!p.multi=[0,2,4]            ;Multiple plot parameters.

!p.region=[0,0,0,0]         ;Plot region.

readin=auto_setup_read_2d_ramp_s1(full_name,numrows=numrows)  ;Read in file

; Read labels, loop sizes, etc.

horiz_label=readin.labels[1]
vert_label = readin.labels[1]
card = readin.labels[0]
   
n_fb = readin.specs[0]
fb_start = readin.specs[1]
fb_step =  readin.specs[2]

n_bias = readin.specs[3]
bias_start = readin.specs[4]
bias_step =  readin.specs[5]

s1_bias=reform(fltarr(n_bias))
for m=0, n_bias-1 do begin
	s1_bias(m) = bias_start + m* bias_step 
endfor

s1_fb=reform(fltarr(n_fb))
for m=0, n_fb-1 do begin
	s1_fb(m) = fb_start + m* fb_step 
endfor

set_plot, 'ps'
device, filename= plot_file, /landscape

a=0
b=399

s1b=''

sizdat=size(readin.data)
new_adc_offset=lonarr(sizdat(3),sizdat(4))
squid_p2p=lonarr(sizdat(3),sizdat(4))
squid_lockrange=lonarr(sizdat(3),sizdat(4))
squid_lockslope=fltarr(sizdat(3),sizdat(4),2)
slope_pnts = 10		;Number of points to fit to find the slope at zero crossing points.
squid_multilock=intarr(sizdat(3),sizdat(4))


;stop

for j=0,n_bias-1 do begin
;	s1b='the 1 set in the config file'
        for kr=0,n_elements(rows)-1 do begin
            k = rows(kr)
	    for i=0, 7 do begin
	        label = 'SA Channel ' + string(i, format='(f3.0)')	
	        plot, s1_fb[a:b]/1000., readin.data[a:b,j,i,k]/1000., xtitle="SQ1_FB"+i_units, ytitle="Voltage"+v_units,$
	        charsize=1.2, xstyle=1, /ynozero,$
	        xrange=[min(s1_fb)/1000., max(s1_fb)/1000.], title= label;, yr=[-30,30]
		;Select adc offsets to be in the largest gap between all slope=0 regions in the v-phi curve
		smnum = 10
		smdat = smooth(readin.data[*,j,i,k],smnum)
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
						downfit = linfit(s1_fb(dnsl(0)-slope_pnts/2:dnsl(0)+slope_pnts/2),readin.data[dnsl(0)-slope_pnts/2:dnsl(0)+slope_pnts/2,j,i,k])
 						squid_lockslope(i,k,0)=downfit(1)
						oplot, [-8,8],[downfit(0)/1000.-8*downfit(1),downfit(0)/1000.+8*downfit(1)], linestyle=1
					endif
					if upsl(0) ne -1 then begin
						upfit = linfit(s1_fb(upsl(0)-slope_pnts/2:upsl(0)+slope_pnts/2),readin.data[upsl(0)-slope_pnts/2:upsl(0)+slope_pnts/2,j,i,k])
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
	    xyouts, .1, 1.0, name_label + ' , '+ label_row , charsize=1.2, /normal
;	    xyouts, 0.7, 1.0, 'sq1 bias = ' + s1b , charsize=1.2, /normal
;	    xyouts, 0.4, 1.1, label_row , charsize=1.2, /normal
	endfor  ; End of loop in 33 rows.
endfor

;new_adc_offset=lonarr(8)
;for i=0,7 do new_adc_offset(i)=mean(readin.data(0,*,i,2))

close, 1
device, /close                  ;close ps

if n_elements(strsplit(file_name, 'p')) gt 1 then begin
    if file_search('/misc/mce_plots',/test_directory) eq '/misc/mce_plots' then begin
        if file_search('/misc/mce_plots/'+ctime,/test_directory) ne '/misc/mce_plots/'+ctime $
                then spawn, 'mkdir /misc/mce_plots/'+ctime
        spawn, 'cp -rf '+plot_file+' /misc/mce_plots/'+ctime
        spawn, 'chgrp -R mceplots /misc/mce_plots/'+ctime
    endif
endif

print,' '
print,'###########################################################################'
print,' '
print,'To view the SQ1 V-phi curves check the file'
print,string(plot_file)
print,' '
print,'###########################################################################'

close, 3
if keyword_set(interactive) then spawn, 'ggv '+plot_file+' &'
fine:
end
