pro auto_setup_sq2servo_plot,file_name,SQ2BIAS=sq2bias,RC=rc,interactive=interactive,SLOPE=slope,lockamp=lockamp,gain=gain, $
                             ramp_start=ramp_start, ramp_step=ramp_step, ramp_count=ramp_count

;  Aug. 21 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from sq2servo_plot.pro 
;  Modified by M. Niemack Sept. 2007.

;  lockamp keyword causes program to select an SAFB value that will put you in the middle of the S2 SQUID response amplitude range 
;	instead of in the middle of the phi-0 range

common sq2_servo_var

;Close all open files. It helps avoid some errors although shouldn't be necessary:
close,/all

;Comunication:
print,''
print,'#############################################################################'
print,'#3) The third step is to run a closed loop on the SQ2 for RC'+strcompress(string(RC),/remove_all)+'.              #'
print,'#   We ramp SQ2 fb and we adjust the SSA fb to keep the target to zero.     #'
print,'#   This will allow us to set the final SSA fb and SQ2 bias.                #'
print,'#############################################################################'
print,''


target=0

;Set file_name_sq2_servo
file_name_sq2_servo=file_name+'_sq2servo'

ctime=string(file_name,format='(i10)')

logfile=ctime+'/'+ctime+'.log'

if not keyword_set(gain) then gain=1./50.
;if RC eq 1 then gain=1./5.

print,'Hardcoding for sq2 fb DAC range!!'
dac_range=65536

; ramp_count is the parameter that will override the defaults.
if not keyword_set(ramp_count) then begin
    ramp_start=0
    ramp_step=160
    ramp_count=400
endif

;Run the shell script:
spawn,'sq2servo '+file_name_sq2_servo+' '+string(sq2bias)+' 0 1 ' + $
  string(ramp_start)+' '+string(ramp_step)+' '+string(ramp_count)+' ' + $
  string(rc)+' '+string(target)+' '+string(gain)+' 1'+ $
  ' >> /data/cryo/current_data/'+logfile,exit_status=status7

if status7 ne 0 then begin
        print,''
        print,'################################################################'
        print,'# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE SQ"SERVO SCRIPT #
        print,'################################################################'
        print,''
        exit,status=7
endif

;Let's define filenames and folders
full_name = '/data/cryo/current_data/' + file_name_sq2_servo
                                                                                                                                                             
;spawn,'ln full_name+' /data/mce_ctimes/'+strmid(file_name_sq2_servo,11)
;spawn,'ln full_name+'.run /data/mce_ctimes/'+strmid(file_name_sq2_servo,11)+'.run'

;Let's drow

set_plot, 'ps'

file_out = '/data/cryo/current_data/analysis/' + file_name_sq2_servo + '.ps'

device, filename=file_out, /landscape


; Read ramp parameters from runfile

openr,1,full_name+'.run'
line=""

repeat readf,1,line until strmid(line,0,10) eq "<par_ramp>"

name=''
par=''
first=''
second=''

readf,1,par
;print, par ;TEST
readf,1,first
readf,1,first
firstarr=strsplit(first,/extract)
first=(firstarr(3))
;print, first ;TEST
readf,1,name
namearr=strsplit(name,/extract)
start_1st=fix(namearr(3))
step_1st=fix(namearr(4))
n_1st=fix(namearr(5))
readf,1,second
readf,1,second
secondarr=strsplit(second,/extract)
second=(secondarr(3))
;print, second ;TEST
readf,1,name
namearr=strsplit(name,/extract)
start_2nd=fix(namearr(3))
step_2nd=fix(namearr(4))
n_2nd=fix(namearr(5))

sq2_bias=start_1st
sq2_bstep=step_1st
n_bias=n_1st
sq2_fb=start_2nd
sq2_fb_s=step_2nd
npts=n_2nd
close,1

; done reading loop parameters from runfile


r0=fltarr(npts,8)
r1 = fltarr(npts,8)
fb0=fltarr(npts,8)
fb1 = fltarr(npts,8)
values = fltarr(16)


; Read sq2servo output from .bias file

openr,1,full_name+'.bias'
readf, 1, line

for n=0, npts-1 do begin
	readf, 1, line
	data=strmid(line, 0)
	reads,data, values
	r1[n,*]=values[0:7]
	fb1[n,*]=values[8:15]
endfor

close, 1

sq2_sweep = (sq2_fb + findgen(npts)*sq2_fb_s) /1000.
!p.multi=[0,2,4]

for j=0,7 do begin
	label = string(j, format='(f4.0)')
	fbmax = max(fb1[10:*,j])/1000
	fbmin=min(fb1[10:*,j])/1000
	plot,sq2_sweep, fb1[*,j]/1000,/ys, ytitle ='SA_FB/1000',$
        xtitle='SQ2_FB/1000', /xs, title='Feed Back, SA Channel '+ label,$
        yrange=[fbmin,fbmax]
	;oplot,sq2_sweep, fb1[*,j]/1000, linestyle=1

	ymin = min(r1[10:*,j])/1000 -2.
	ymax = max(r1[10:*,j])/1000 +2
	plot, sq2_sweep, r1[*,j]/1000, ytitle=' AD_reading/1000',$
        xtitle='SQ2_FB/1000',$
        /ys, /xs, title='AD Output, SA Channel'+ label,$
   	yrange=[ymin, ymax]
	;oplot,sq2_sweep, r1[*,j]/1000., linestyle=1

	label = 'SQ2_BIAS = ' + string(sq2_bias, format='(f7.0)')
	xyouts, 0.1, 1.01, label, /normal	;print value of sq_bias
	xyouts, 0.99,1.01, full_name, /normal, alignment=1.0   ;print filename as title
endfor  

device, /close

;spawn,'ggv '+file_out+' &';run the ggv to see the plot file (commented in the auto_setup version)

target_half_point_ch_by_ch=lonarr(8)
fb_half_point_ch_by_ch=lonarr(8)
SQ2_target=lonarr(8)
SQ2_feedback=lonarr(8)
deriv_fb1=fb1
sq2_v_phi=fb1
				
for chan=0,7 do begin	;calculate the derivatives of the V-phi plots
;	deriv_fb1(*,chan)=smooth(deriv(sq2_sweep(*),fb1(*,chan)),10)
; Changed to smooth before derivative. MDN 4-2-2008
	deriv_fb1(*,chan)=deriv(sq2_sweep(*),smooth(fb1(*,chan),10))
	sq2_v_phi(*,chan)=smooth(fb1(*,chan),10)
endfor

print,''
print,'###########################################################################'
print,'SQ2 bias, and SA fb channel by channel:'
print,'###########################################################################'

; Elia analyses only samples 100:350 of a 400 point curve.

lo_index = ramp_count / 4.
hi_index = ramp_count * 7. / 8.
for chan=0,7 do begin
	print,'Channel:',chan
		; Added fbmn (mean value) check for finding period (includes 3 lines below) 4-2-2008 MDN & JA
		fbmn = (max(sq2_v_phi(lo_index:hi_index,chan)) - min(sq2_v_phi(lo_index:hi_index,chan)))/2.+min(sq2_v_phi(lo_index:hi_index,chan))
		fbmax = (max(sq2_v_phi(lo_index:hi_index,chan)))
		fbmin = (min(sq2_v_phi(lo_index:hi_index,chan)))
		if slope lt 0 then begin
			min_point=min(sq2_v_phi(lo_index:hi_index,chan),ind_min)
			ind_min=lo_index+ind_min
			ind_pos_der=where(deriv_fb1(0:ind_min-5,chan) gt 0 and sq2_v_phi(0:ind_min-5,chan) gt fbmn and sq2_v_phi(0:ind_min-5,chan) le fbmax)
			if n_elements(ind_pos_der) eq 1 then ind_pos_der=1
			ind_max=max(ind_pos_der)
		endif else begin
			max_point=max(sq2_v_phi(lo_index:hi_index,chan),ind_max)
                        ind_max=lo_index+ind_max
                        ind_neg_der=where(deriv_fb1(0:ind_max-5,chan) lt 0  and sq2_v_phi(0:ind_max-5,chan) lt fbmn and sq2_v_phi(0:ind_min-5,chan) ge fbmin)
                        if n_elements(ind_neg_der) eq 1 then ind_neg_der=1
                        ind_min=max(ind_neg_der)
		endelse
		;if fb1(ind_max,chan) gt 65535 then ind_max=ind_max+$
		;where(abs(fb1(ind_max:ind_min,chan)-65535) eq min(abs(fb1(ind_max:ind_min,chan)-65535)))
		if keyword_set(lockamp) then begin
			fb_mean = (fb1(ind_min,chan)+fb1(ind_max,chan))/2.
			print, 'Locking at middle of amplitude range instead of middle of phi-0 range'
			if ind_min lt ind_max then begin
				fb_close = min(abs(fb1(ind_min:ind_max,chan)-fb_mean),fb_pnt)
				ind_half_point = fb_pnt + ind_min
			endif else begin
				fb_close = min(abs(fb1(ind_max:ind_min,chan)-fb_mean),fb_pnt)
				ind_half_point = fb_pnt + ind_max ;where(abs(fb1(ind_max:ind_min)-fb_mean) eq fb_close) + ind_max
			endelse
			target_half_point_ch_by_ch(chan)=round(fb1(ind_half_point,chan))
			fb_half_point_ch_by_ch(chan)=round(1000.*sq2_sweep(ind_half_point))
		endif else begin
			ind_half_point=round((ind_min+ind_max)/2)
			target_half_point_ch_by_ch(chan)=round(fb1(ind_half_point,chan))
			fb_half_point_ch_by_ch(chan)=round(1000.*sq2_sweep(ind_half_point))
		endelse
		print,'target  @ half point=',target_half_point_ch_by_ch(chan)
		print,'sq2_feedback   @ half point=',fb_half_point_ch_by_ch(chan)	
	;print,' '
	print,'###########################################################################'
	;print,' '
;stop
endfor

SQ2_target=target_half_point_ch_by_ch
SQ2_feedback=fb_half_point_ch_by_ch



;SQ2_target(2)=66000		;for testing purposes
;SQ2_feedback(3)=-5

for chan=0,7 do begin
	if (SQ2_feedback(chan) ge dac_range) or (SQ2_feedback(chan) le 0) then begin
		SQ2_feedback(chan)=dac_range/2
		print,' '
		print,'###########################################################################'
		print,' '
		print,'WARNING: SQ2 fb of channel'+string(chan)+' found on the SQ2 V-phi curve has' 
		print,'         been set to 32000 bacause the program found a non valid value'
		print,' '
		print,'###########################################################################'		
	endif
endfor

!p.multi=[0,2,4]


file_name_sq2_points=file_name+'_sq2_points'
plot_file = '/data/cryo/current_data/'+'analysis/' + file_name_sq2_points + '.ps'
print,' '
print,'###########################################################################'
print,' '
print,'To view the SQ2 locking points check '+string(plot_file)
print,' '
print,'###########################################################################'
charsz=1
set_plot, 'ps'
device, filename= plot_file, /landscape

for j=0,7 do begin
	label = string(j, format='(f4.0)')
	fbmax = max(fb1[10:*,j])/1000
	fbmin=min(fb1[10:*,j])/1000
	plot,sq2_sweep, fb1[*,j]/1000,/ys, ytitle ='SA_FB/1000',$
        xtitle='SQ2_FB/1000', /xs, title='Feed Back, SA Channel '+ label,$
        yrange=[fbmin,fbmax],charsize=charsz
	;oplot,sq2_sweep, fb1[*,j]/1000, linestyle=1
	oplot, [sq2_sweep(0),sq2_sweep(n_elements(sq2_sweep)-1)],[SQ2_target(j),SQ2_target(j)]/1000.
	oplot, [SQ2_feedback(j),SQ2_feedback(j)]/1000.,[-200,200]
endfor  

device, /close                  ;close ps

if file_search('/misc/mce_plots',/test_directory) eq '/misc/mce_plots' then begin
        if file_search('/misc/mce_plots/'+ctime,/test_directory) ne '/misc/mce_plots/'+ctime $
		then spawn, 'mkdir /misc/mce_plots/'+ctime
        spawn, 'cp -rf '+plot_file+' /misc/mce_plots/'+ctime
        spawn, 'chgrp -R mceplots /misc/mce_plots/'+ctime
endif

if keyword_set(interactive) then spawn, 'ggv '+plot_file+' &'

end 
