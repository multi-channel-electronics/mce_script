pro auto_setup_ramp_sq1_bias_plot, file_name,RC=rc,interactive=interactive,numrows=numrows, $
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
print,'#5) The optional fifth step is to check the v-phi curves from sweeping    #'
print,'#   the tes bias by running ramp_sq1_fb                                   #'
print,'###########################################################################'
print,''

default_folder = '/data/cryo/'

default_date = 'current_data/'

date= default_date

folder= default_folder

logfile=string(file_name,format='(i10)')

logfile=logfile+'/'+logfile+'.log'

user_status = auto_setup_userword(rc)
spawn,'ramp_sq1_bias '+file_name+' '+string(rc)+ ' >> /data/cryo/current_data/'+logfile,exit_status=status22
if status22 ne 0 then begin
        print,''
        print,'##########################################################################################'
        print,'# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE RAMP_SQ1 SCRIPT AND SWEEPING THE TES BIAS #'
        print,'##########################################################################################'
        print,''
        exit,status=22
endif

cd = ''
;Set filename.
full_name=folder+date+file_name
openr, 3, '/data/cryo/current_data_name'
readf, 3,  cd
close, 3
name_label = '/data/cryo' + '/' + cd + '/' + file_name 

rf = mas_runfile(full_name+'.run')
loop_params = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
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

readin=auto_setup_read_2d_ramp_s1(full_name)  ;Read in file

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
;new_adc_offset=lonarr(sizdat(3),sizdat(4))
;squid_p2p=lonarr(sizdat(3),sizdat(4))
;squid_lockrange=lonarr(sizdat(3),sizdat(4))

;stop

print, 'NUMROWS is hardcoded to 33 in the for k loop here.'
; print, 'Ok, well  is'+string(numrows)
for j=0,n_bias-1 do begin
	s1b='the 1 set in the config file'
	for k=0,numrows-1 do begin  ;  A new loop to put one address value per page.
	    for i=0, 7 do begin
	        label = 'SA Channel ' + string(i, format='(f3.0)')	
	        plot, s1_fb[a:b]/1000., readin.data[a:b,j,i,k]/1000., xtitle="TES_bias"+i_units, ytitle="Voltage"+v_units,$
	        charsize=1.2, xstyle=1, /ynozero,$
	        xrange=[min(s1_fb)/1000., max(s1_fb)/1000.], title= label;, yr=[-30,30]
		;Select adc offsets to be in the largest gap between all slope=0 regions in the v-phi curve
		smnum = 5
		smdat = smooth(readin.data[*,j,i,k],smnum)		
		smdat_der = smdat - shift(smdat,-1)
		zero_slope = fltarr(b+1)
		for l=a+smnum,b-1-smnum do begin
			if smdat_der(l) le 0 and smdat_der(l+1) ge 0 then zero_slope(l)=1
			if smdat_der(l) ge 0 and smdat_der(l+1) le 0 then zero_slope(l)=1
		endfor
		low_sl = where(zero_slope eq 1)
		if low_sl(0) ne -1 then begin
			oplot, s1_fb[low_sl(*)]/1000.,smdat(low_sl(*))/1000.,psym=1
			oplot, [s1_fb(a),s1_fb(b)],[0.,0.],linestyle=2
			nls = n_elements(low_sl)
			if nls gt 1 then begin
				low_sl_order = sort(smdat(low_sl))
				low_sl_diff = abs(smdat(low_sl(low_sl_order(0:nls-2)))-smdat(low_sl(low_sl_order(1:nls-1))))
				select = where(low_sl_diff eq max(low_sl_diff))
				if select(0) eq -1 or n_elements(select) gt 1 then begin
;					print, 'You have adc_offset selection problems on Column '$
;						+strtrim(i,1)+' Row '+strtrim(k)+'.  Take a deep breath.'
;                	                new_adc_offset(i,k)=0.
;		                        squid_lockrange(i,k)=0.
				endif else begin
;					new_adc_offset(i,k)=(smdat(low_sl(low_sl_order(select(0))))+smdat(low_sl(low_sl_order(select(0)+1))))/2
;					squid_lockrange(i,k)=abs(smdat(low_sl(low_sl_order(select(0))))-smdat(low_sl(low_sl_order(select(0)+1))))
				endelse
			endif else begin
;        	                new_adc_offset(i,k)=0.
;				squid_lockrange(i,k)=0.
	                endelse
		endif else begin
;			new_adc_offset(i,k)=0.
;			squid_lockrange(i,k)=0.
		endelse
;		squid_p2p(i,k)=abs(max(smdat)-min(smdat))
;		new_adc_offset(i,k)=(max(smdat)+min(smdat))/2  ; Note: Old method of selection used smnum=5
	    endfor  ; end of plotting loop in 8 columns.
	    label_bias = 'sq1 bias = ' + s1b
	    label_row='row #'+string(k) 
	    xyouts, .1, 1.0, name_label , charsize=1.2, /normal
	    xyouts, 0.7, 1.0, label_bias , charsize=1.2, /normal
	    xyouts, 0.4, 1.0, label_row , charsize=1.2, /normal
	endfor  ; End of loop in 33 rows.
endfor

;new_adc_offset=lonarr(8)
;for i=0,7 do new_adc_offset(i)=mean(readin.data(0,*,i,2))

close, 1
device, /close                  ;close ps

print,' '
print,'###########################################################################'
print,' '
print,'To view the SQ1 V-phi curves check the file '+string(plot_file)
print,' '
print,'###########################################################################'

close, 3
if keyword_set(interactive) then spawn, 'ggv '+plot_file+' &'
fine:
end
