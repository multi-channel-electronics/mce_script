pro auto_setup_sq2servo_plot,file_name,SQ2BIAS=sq2bias,RC=rc,interactive=interactive,SLOPE=slope,lockamp=lockamp,gain=gain, $
                             ramp_start=ramp_start, ramp_step=ramp_step, ramp_count=ramp_count, $
                             bias_start=bias_start, bias_step=bias_step, bias_count=bias_count, $
                             acq_id=acq_id, quiet=quiet, poster=poster, no_analysis=no_analysis

;  Aug. 21 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from sq2servo_plot.pro 
;  Modified by M. Niemack Sept. 2007.

;  lockamp keyword causes program to select an SAFB value that will put you in the middle of the S2 SQUID response amplitude range 
;	instead of in the middle of the phi-0 range

common sq2_servo_var

this_script = 'sq2servo_plot'

;Init
if not keyword_set(acq_id) then acq_id = 0

;Close all open files. It helps avoid some errors although shouldn't be necessary:
close,/all

;Communication:
RC_name = strcompress('RC'+string(RC),/remove_all)
if not keyword_set(quiet) then begin
    print,''
    print,'#############################################################################'
    print,'#3) The third step is to run a closed loop on the SQ2 for RC'+strcompress(string(RC),/remove_all)+'.              #'
    print,'#   We ramp SQ2 fb and we adjust the SSA fb to keep the target to zero.     #'
    print,'#   This will allow us to set the final SSA fb and SQ2 bias.                #'
    print,'#############################################################################'
    print,''
endif else begin
    if quiet le 1 then print,this_script + ' : starting for '+RC_name
endelse

target=0

;Set file_name_sq2_servo
file_name_sq2_servo=file_name+'_sq2servo'

ctime=string(file_name,format='(i10)')

logfile=ctime+'/'+ctime+'.log'

if not keyword_set(gain) then gain=1./50.
;if RC eq 1 then gain=1./5.

;print,'Hardcoding for sq2 fb DAC range!!'
dac_range=65536

; ramp_count is the parameter that will override the defaults.
if not keyword_set(ramp_count) then begin
    ramp_start=0
    ramp_step=160
    ramp_count=400
endif

;Run the servo program
user_status = auto_setup_userword(rc)
if keyword_set(bias_count) then begin
    ; Ramp the SQ2 bias as well as the SQ2 FB
    spawn_str = 'sq2servo '+file_name_sq2_servo+' '+ $
      string(bias_start)+' '+string(bias_step)+' '+string(bias_count)+' '+ $
      string(ramp_start)+' '+string(ramp_step)+' '+string(ramp_count)+' ' + $
      string(rc)+' '+string(target)+' '+string(gain)+' 0'+ $
      ' >> /data/cryo/current_data/'+logfile
endif else begin
    ; Ramp the SQ2 FB without changing the SQ2 biases.
    spawn_str = 'sq2servo '+file_name_sq2_servo+' '+string(sq2bias)+' 0 1 ' + $
      string(ramp_start)+' '+string(ramp_step)+' '+string(ramp_count)+' ' + $
      string(rc)+' '+string(target)+' '+string(gain)+' 1'+ $
      ' >> /data/cryo/current_data/'+logfile
endelse
spawn,spawn_str,exit_status=status7

if status7 ne 0 then begin
    if keyword_set(quiet) then begin
        print,this_script + 'error '+string(status7)+' from spawn of ' +spawn_str
    endif else begin
        print,''
        print,'################################################################'
        print,'# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE SQ"SERVO SCRIPT #
        print,'################################################################'
        print,''
        exit,status=7
    endelse
endif

;Let's define filenames and folders
full_name = '/data/cryo/current_data/' + file_name_sq2_servo
     
; Link and register
rf = mas_runfile(full_name+'.run')
loop_params_b = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
loop_params_f = mas_runparam(rf,'par_ramp','par_step loop2 par1',/long)
reg_status = auto_setup_register(acq_id, 'tune_servo', full_name, loop_params_b[2]*loop_params_f[2]) 
                                                                                                                                                        
; END ACQUISITION

; BEGIN ANALYSIS AND PLOTTING

; Rename the loop parameters.

sq2_bias = loop_params_b[0]
sq2_bstep = loop_params_b[1]
n_bias = loop_params_b[2]

input_fb = loop_params_f[0]
input_fb_s = loop_params_f[1]
npts = loop_params_f[2]


r1 = fltarr(npts,8)
fb1 = fltarr(npts,8)
values = fltarr(16)


; Read sq2servo output from .bias file

openr,lun,/get_lun,full_name+'.bias'
line = ''
readf,lun, line
for i=0, npts-1 do begin
	readf,lun, line
	data=strmid(line, 0)
	reads,data, values
	r1[i,*]=values[0:7]
	fb1[i,*]=values[8:15]
endfor
free_lun,lun

input_sweep = (input_fb + findgen(npts)*input_fb_s) /1000.
;Let's draw

set_plot, 'ps'
file_out = '/data/cryo/current_data/analysis/' + file_name_sq2_servo + '.ps'
device, filename=file_out, /landscape
!p.multi=[0,2,4]

for j=0,7 do begin
	label = string(j, format='(f4.0)')
	fbmax = max(fb1[10:*,j])/1000
	fbmin=min(fb1[10:*,j])/1000
	plot,input_sweep, fb1[*,j]/1000,/ys, ytitle ='SA_FB/1000',$
        xtitle='SQ2_FB/1000', /xs, title='Feed Back, SA Channel '+ label,$
        yrange=[fbmin,fbmax]
	;oplot,input_sweep, fb1[*,j]/1000, linestyle=1

	ymin = min(r1[10:*,j])/1000 -2.
	ymax = max(r1[10:*,j])/1000 +2
	plot, input_sweep, r1[*,j]/1000, ytitle=' AD_reading/1000',$
        xtitle='SQ2_FB/1000',$
        /ys, /xs, title='AD Output, SA Channel'+ label,$
   	yrange=[ymin, ymax]
	;oplot,input_sweep, r1[*,j]/1000., linestyle=1

	label = 'SQ2_BIAS = ' + string(sq2_bias, format='(f7.0)')
	xyouts, 0.1, 1.01, label, /normal	;print value of sq_bias
	xyouts, 0.99,1.01, full_name, /normal, alignment=1.0   ;print filename as title
endfor  

device, /close


; ANALYSIS REALLY STARTS HERE...
if keyword_set(no_analysis) then return

;spawn,'ggv '+file_out+' &';run the ggv to see the plot file (commented in the auto_setup version)

target_half_point_ch_by_ch=lonarr(8)
fb_half_point_ch_by_ch=lonarr(8)
SQ2_target=lonarr(8)
SQ2_feedback=lonarr(8)
deriv_fb1=fb1
sq2_v_phi=fb1
				
for chan=0,7 do begin	;calculate the derivatives of the V-phi plots
;	deriv_fb1(*,chan)=smooth(deriv(input_sweep(*),fb1(*,chan)),10)
; Changed to smooth before derivative. MDN 4-2-2008
	deriv_fb1(*,chan)=deriv(input_sweep(*),smooth(fb1(*,chan),10))
	sq2_v_phi(*,chan)=smooth(fb1(*,chan),10)
    endfor

if not keyword_set(quiet) then begin
    print,''
    print,'###########################################################################'
    print,'SQ2 bias, and SA fb channel by channel:'
    print,'###########################################################################'
    if keyword_set(lockamp) then $
      print, 'Locking at middle of amplitude range instead of middle of phi-0 range'

    print,' Channel                   Target@half sq2_fb@half '
    print,'---------------------------------------------------'
endif


; Elia analyses only samples 100:350 of a 400 point curve.

lo_index = ramp_count / 2.
hi_index = ramp_count * 7. / 8.
for chan=0,7 do begin
		; Added fbmn (mean value) check for finding period (includes 3 lines below) 4-2-2008 MDN & JA
		fbmn = (max(sq2_v_phi(lo_index:hi_index,chan)) - min(sq2_v_phi(lo_index:hi_index,chan)))/2.+min(sq2_v_phi(lo_index:hi_index,chan))
		fbmax = (max(sq2_v_phi(lo_index:hi_index,chan)))
		fbmin = (min(sq2_v_phi(lo_index:hi_index,chan)))
		if slope lt 0 then begin
			min_point=min(sq2_v_phi(lo_index:hi_index,chan),ind_min)
			ind_min=lo_index+ind_min
			ind_pos_der=where(deriv_fb1(10:ind_min-5,chan) gt 0 and sq2_v_phi(10:ind_min-5,chan) gt fbmn and sq2_v_phi(10:ind_min-5,chan) le fbmax)
			ind_pos_der=ind_pos_der+10
			if n_elements(ind_pos_der) eq 1 then ind_pos_der=1
			ind_max=max(ind_pos_der)
		endif else begin
			max_point=max(sq2_v_phi(lo_index:hi_index,chan),ind_max)
                        ind_max=lo_index+ind_max
                        ind_neg_der=where(deriv_fb1(10:ind_max-5,chan) lt 0 and sq2_v_phi(10:ind_max-5,chan) lt fbmn and sq2_v_phi(10:ind_max-5,chan) ge fbmin)
			ind_neg_der=ind_neg_der+10
                        if n_elements(ind_neg_der) eq 1 then ind_neg_der=1
                        ind_min=max(ind_neg_der)
		endelse
		;if fb1(ind_max,chan) gt 65535 then ind_max=ind_max+$
		;where(abs(fb1(ind_max:ind_min,chan)-65535) eq min(abs(fb1(ind_max:ind_min,chan)-65535)))
		if keyword_set(lockamp) then begin
			fb_mean = (fb1(ind_min,chan)+fb1(ind_max,chan))/2.
; 			print, 'Locking at middle of amplitude range instead of middle of phi-0 range'
			if ind_min lt ind_max then begin
				fb_close = min(abs(fb1(ind_min:ind_max,chan)-fb_mean),fb_pnt)
				ind_half_point = fb_pnt + ind_min
			endif else begin
				fb_close = min(abs(fb1(ind_max:ind_min,chan)-fb_mean),fb_pnt)
				ind_half_point = fb_pnt + ind_max ;where(abs(fb1(ind_max:ind_min)-fb_mean) eq fb_close) + ind_max
			endelse
			target_half_point_ch_by_ch(chan)=round(fb1(ind_half_point,chan))
			fb_half_point_ch_by_ch(chan)=round(1000.*input_sweep(ind_half_point))
		endif else begin
			ind_half_point=round((ind_min+ind_max)/2)
			target_half_point_ch_by_ch(chan)=round(fb1(ind_half_point,chan))
			fb_half_point_ch_by_ch(chan)=round(1000.*input_sweep(ind_half_point))
                endelse

                if not keyword_set(quiet) then begin
                    print,format='(i4, i31, i12)',chan, $
                      target_half_point_ch_by_ch(chan), fb_half_point_ch_by_ch(chan)
                endif

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
if not keyword_set(quiet) then begin
    print,' '
    print,'###########################################################################'
    print,' '
    print,'To view the SQ2 locking points check'
    print,string(plot_file)
    print,' '
    print,'###########################################################################'
endif
charsz=1
set_plot, 'ps'
device, filename= plot_file, /landscape

!p.region=[0,0,0,0]             ;Plot region.
!y.omargin=[0.,5.]              ;Leave room at top for page title

for j=0,7 do begin
	label = string(j, format='(f4.0)')
	fbmax = max(fb1[10:*,j])/1000
	fbmin=min(fb1[10:*,j])/1000
	plot,input_sweep, fb1[*,j]/1000,/ys, ytitle ='SA_FB/1000',$
        xtitle='SQ2_FB/1000', /xs, title='Feed Back, SA Channel '+ label,$
        yrange=[fbmin,fbmax],charsize=charsz
	;oplot,input_sweep, fb1[*,j]/1000, linestyle=1
	oplot, [input_sweep(0),input_sweep(n_elements(input_sweep)-1)],[SQ2_target(j),SQ2_target(j)]/1000.
	oplot, [SQ2_feedback(j),SQ2_feedback(j)]/1000.,[-200,200]
endfor  

device, /close                  ;close ps

if keyword_set(poster) then begin
   f = strsplit(plot_file,'/',/extract)
   auto_post_plot,poster,filename=f[n_elements(f)-1]
endif

if keyword_set(interactive) then spawn, 'ggv '+plot_file+' &'

end 
