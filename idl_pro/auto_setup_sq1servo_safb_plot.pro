pro auto_setup_sq1servo_safb_plot,file_name,SQ1BIAS=sq1bias,RC=rc,ROW=row,numrows=numrows,interactive=interactive

;  Aug. 21 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from sq1servo_plot.pro 


common sq1_servo_var

;Close all open files. It helps avoid some errors although shouldn't be necessary:
close,/all

;Communication:
print,''
print,'###########################################################################'
print,'#4b) The 2nd part of the forth step is to run a closed loop on the SQ1. We ramp the SQ1 fb #'
print,'#   and we adjust the SA fb to leave the target to zero. This will allow  #'
print,'#   us to set the final SA fb for the columns that have bad S2 FB lines.  #'
print,'###########################################################################'
print,''


target=0

;Set file_name_sq1_servo
file_name_sq1_servo=file_name+'_sq1_servo_safb'

;Run the shell script:
;spawn,'sq1servo '+file_name_sq1_servo+' '+string(sq1bias)+' 0 1 -8000 40 400 '+string(rc)+' '+string(target)+' '+string(numrows)
spawn,'sq1servo_safb '+file_name_sq1_servo+' '+string(sq1bias)+' 0 1 -8000 40 400 '+string(rc)+' '+string(target)+' '+string(numrows)+' 1' + ' >> /data/cryo/current_data/'+file_name+'.log'

set_plot, 'ps'

;Let's define filenames and folders
full_name = '/data/cryo/current_data/' + file_name_sq1_servo

openr,1,full_name
line=""

file_out2 = '/data/cryo/current_data/analysis/' + file_name_sq1_servo + '.ps'

cn = ''
openr, 3, '/data/cryo/current_data_name'
readf, 3, cn
file_label = '/data/cryo/current_data/analysis/' + cn + '/' + file_name
close, 3

device, filename=file_out2, /landscape

readf, 1, line

reads, line, sq2_bias, format='(8x,I)'
print, 'SQ1_BIAS:', sq2_bias 

readf, 1, line
reads, line, sq2_bstep, format='(9x,I)'
print, 'SQ1_BSTEP:', sq2_bstep 
 
readf, 1, line
reads, line, n_bias, format='(6x,I)'

readf, 1, line
reads, line, SQ2_FB, format='(8x,I)'
print, 'SQ1_FB:', sq2_fb 

readf, 1, line
reads, line, sq2_fb_s, format='(9x,I)'
print, 'SQ1_FB_S:', sq2_fb_s 

readf, 1, line
reads, line, npts, format='(6x,I)'

r0=fltarr(npts,8)
r1 = fltarr(npts,8)
fb0=fltarr(npts,8)
fb1 = fltarr(npts,8)
values = fltarr(8)

readf, 1, line
readf, 1, line
print,'Rows selected='+line

for n=0, npts-1 do begin

	readf, 1, line
	data=strmid(line, 14,72)
	reads, data, values
	r0[n,*]=values[*]

	readf, 1, line
	data=strmid(line, 14,72)
	reads, data, values
	fb0[n,*]=values[*]

	readf, 1, line

	readf, 1, line
	data=strmid(line, 14,72)
	reads, data, values
	r1[n,*]=values[*]

	readf, 1, line
	data=strmid(line, 14,72)
	reads, data, values
	fb1[n,*]=values[*]

	readf, 1, line

endfor

close, 1

sq2_sweep = (sq2_fb + findgen(npts)*sq2_fb_s) /1000.
!p.multi=[0,2,4]

for j=0,7 do begin

	label = string(j, format='(f4.0)')

	fbmax = max(fb0[10:*,j] )/1000.
	fbmin = min(fb0[10:*,j] )/1000.
	plot,sq2_sweep, fb0[*,j]/1000,/ys, ytitle ='SA_FB/1000',$
        xtitle='SQ1_FB/1000', /xs, title='Feed Back, SA Channel '+ label
	oplot,sq2_sweep, fb1[*,j]/1000, linestyle=1

	rmax = max( r1[10:*,j])/1000. + 2.
	rmin = min( r1[10:*,j])/1000.-2.
	plot, sq2_sweep, r0[*,j]/1000, ytitle=' AD_reading/1000',$
        xtitle='SQ1_FB/1000',$
	yrange=[rmin, rmax], /ys, /xs, title='AD Output, SA Channel'+ label
	oplot,sq2_sweep, r1[*,j]/1000., linestyle=1

	label = 'SQ1_BIAS = ' + string(sq2_bias, format='(f7.0)')
	xyouts, 0.1, 1.01, label, /normal	;print value of sq_bias
	xyouts, 0.99,1.01, file_label, /normal, alignment=1.0   ;print filename as title

endfor  

device, /close
;spawn,'ggv '+file_out2+' &'

close,3


target_half_point_ch_by_ch=lonarr(8)
fb_half_point_ch_by_ch=lonarr(8)
SQ1_target_sa=lonarr(8)
SQ1_feedback=lonarr(8)
deriv_fb1=fb1
sq1_v_phi=fb1
				
for chan=0,7 do begin	;calculate the derivatives of the V-phi plots
	deriv_fb1(*,chan)=smooth(deriv(sq2_sweep(*),fb1(*,chan)),5)
	sq1_v_phi(*,chan)=smooth(fb1(*,chan),5)
endfor

print,''
print,'###########################################################################'
print,'For Channels with open SQ2 fb, we have SQ1 bias, and SA fb channel by channel:'
print,'###########################################################################'
for chan=0,7 do begin
	print,'Channel:',chan
		min_point=min(sq1_v_phi(150:350,chan),ind_min)
		ind_min=150+ind_min
		ind_pos_der=where(deriv_fb1(0:ind_min-5,chan) gt 0)
		if n_elements(ind_pos_der) eq 1 then ind_pos_der=1
		ind_max=max(ind_pos_der)
		;if fb1(ind_max,chan) gt 65535 then ind_max=ind_max+$
		;where(abs(fb1(ind_max:ind_min,chan)-65535) eq min(abs(fb1(ind_max:ind_min,chan)-65535)))
		ind_half_point=round((ind_min+ind_max)/2)
		target_half_point_ch_by_ch(chan)=round(fb1(ind_half_point,chan))
		fb_half_point_ch_by_ch(chan)=round(1000.*sq2_sweep(ind_half_point))
		print,'target  @ half point=',target_half_point_ch_by_ch(chan)
		print,'sq1_feedback   @ half point=',fb_half_point_ch_by_ch(chan)	
	;print,' '
	print,'###########################################################################'
	;print,' '
;stop
endfor

SQ1_target_sa=target_half_point_ch_by_ch
SQ1_feedback=fb_half_point_ch_by_ch



;SQ2_target(2)=66000		;for testing purposes
;SQ2_feedback(3)=-5

for chan=0,7 do begin
	if (SQ1_feedback(chan) gt 8000) or (SQ1_feedback(chan) le -8000) then begin
		SQ1_feedback(chan)=0
		print,' '
		print,'###########################################################################'
		print,' '
		print,'WARNING: SQ1 fb of channel'+string(chan)+' found on the SQ1 V-phi curve has' 
		print,'         been set to 0 (midrange) bacause the program found a non valid value'
		print,' '
		print,'###########################################################################'		
	endif
endfor

!p.multi=[0,2,4]



file_name_sq1_points=file_name+'_sq1_points_safb'
plot_file = '/data/cryo/current_data/'+'analysis/' + file_name_sq1_points + '.ps'
print,' '
print,'###########################################################################'
print,' '
print,'To view the SQ1 locking points check '+string(plot_file)
print,' '
print,'###########################################################################'
charsz=1
set_plot, 'ps'
device, filename= plot_file, /landscape

for j=0,7 do begin
	label = string(j, format='(f4.0)')
	fbmax = max(fb0[10:*,j])/1000
	fbmin=min(fb0[10:*,j])/1000
	plot,sq2_sweep, fb0[*,j]/1000,/ys, ytitle ='SA_FB/1000',$
        xtitle='SQ1_FB/1000', /xs, title='Feed Back, SA Channel '+ label,$
        yrange=[fbmin,fbmax],charsize=charsz
	oplot,sq2_sweep, fb1[*,j]/1000, linestyle=1
	oplot, [sq2_sweep(0),sq2_sweep(n_elements(sq2_sweep)-1)],[SQ1_target_sa(j),SQ1_target_sa(j)]/1000.
	oplot, [SQ1_feedback(j),SQ1_feedback(j)]/1000.,[-200,200]
endfor  
device, /close                  ;close ps

if keyword_set(interactive) then spawn, 'ggv '+plot_file+' &'

end 
