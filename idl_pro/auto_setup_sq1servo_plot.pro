pro auto_setup_sq1servo_plot,file_name,SQ1BIAS=sq1bias,RC=rc,ROW=row,numrows=numrows, $
                             interactive=interactive,slope=slope,sq2slope=sq2slope, $
                             gain=gain,lock_rows=lock_rows, $
                             ramp_start=ramp_start, ramp_step=ramp_step, ramp_count=ramp_count, $
                             use_bias_file=use_bias_file, use_run_file=use_run_file, $
                             base_folder=base_folder, $
                             super_servo=super_servo, acq_id=acq_id, poster=poster

;  Aug. 21 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from sq1servo_plot.pro 

common sq1_servo_var

;Init
if not keyword_set(acq_id) then acq_id = 0

; For maximum meaningfullness, if a bias file is passed don't print
; the banner and instead indicate the bias file

if not keyword_set(use_bias_file) then begin
;Communication:
    print,''
    print,'#############################################################################'
    print,'#4) The fourth step is to run a closed loop on the SQ1 for RC'+strcompress(string(RC),/remove_all)+'.             #'
    print,'#   We ramp SQ1 fb and we adjust the SQ2 fb to keep the target to zero.     #'
    print,'#   This will allow us to set the final SQ2 fb and SQ1 bias.                #'
    print,'#############################################################################'
    print,''
endif else begin
    print,'Reading biases from file: ', use_bias_file
endelse

target=0

;Set file_name_sq1_servo
file_name_sq1_servo=file_name+'_sq1servo'
ctime=string(file_name,format='(i10)')
if not keyword_set(base_folder) then $
   base_folder = '/data/cryo/current_data/'
full_name = base_folder + file_name_sq1_servo

logfile=ctime+'/'+ctime+'.log'

; ramp_count is the parameter that will override the defaults.
if not keyword_set(ramp_count) then begin
    ramp_start=-8000
    ramp_step=40
    ramp_count=400
endif

if not keyword_set(gain) then gain = 1./100


;Run the sq1servo program unless the user has passed in a results file.

if not keyword_set(use_bias_file) then begin

    ; Servo arguments, sheesh
    servo_args = '-p 50 ' + $
      file_name_sq1_servo + ' ' + $
      string(sq1bias)+' 0 1 '+ $ ;
      string(ramp_start)+' '+string(ramp_step)+' '+string(ramp_count)+' '+ $
      string(rc)+' '+string(target)+' '+string(numrows)+' '+string(gain)+' 1 '
    
    ; Choose servo program based on super_servo switch
    if keyword_set(super_servo) then $
      servo_cmd = 'sq1servo_all' $
    else $
      servo_cmd = 'sq1servo'
    
    ; Go go go
    user_status = auto_setup_userword(rc)
    spawn,servo_cmd+' '+servo_args+' >> ' + base_folder + logfile,exit_status=status10
    if status10 ne 0 then begin
        print,''
        print,'################################################################'
        print,'# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE SQ1SERVO SCRIPT #'
        print,'################################################################'
        print,''
        exit,status=10
    endif

    ; Link and register
    rf = mas_runfile(full_name+'.run')
    loop_params_b = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
    loop_params_f = mas_runparam(rf,'par_ramp','par_step loop2 par1',/long)
    reg_status = auto_setup_register(acq_id, 'tune_servo', full_name, loop_params_b[2]*loop_params_f[2]) 
    full_bias_filename = full_name+'.bias'
endif else begin
    full_bias_filename = base_folder + use_bias_file
    rf = mas_runfile(full_name+'.run')
    loop_params_b = mas_runparam(rf,'par_ramp','par_step loop1 par1',/long)
    loop_params_f = mas_runparam(rf,'par_ramp','par_step loop2 par1',/long)
endelse

; Super servo exits now; we'll re-enter with each bias file (or whatever)
if keyword_set(super_servo) then return


; Analysis and plotting begins

; Read the loop parameters from the run file

sq1_bias = loop_params_b[0]
sq1_bstep = loop_params_b[1]
n_bias = loop_params_b[2]

input_fb = loop_params_f[0]
input_fb_s = loop_params_f[1]
npts = loop_params_f[2]


; Read sq1servo output from .bias file
r1 = fltarr(npts,8)
fb1 = fltarr(npts,8)
values = fltarr(16)

openr,lun,/get_lun,full_bias_filename
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

file_out2 = base_folder + '/analysis/' + file_name_sq1_servo + '.ps'
input_sweep = (input_fb + findgen(npts)*input_fb_s) /1000.

columns = transpose(lindgen(8) + (rc-1)*8)
rows = lock_rows[columns]
labels = string([columns, rows], format='("Feed Back, SA Column ",I2," Row ",I2)')
errlabels = string([columns, rows], format='("ADC Output, SA Column ",I2," Row ",I2)')

auto_setup_plot_servo,file_out2, $
                      input_sweep, transpose(fb1)/1000., transpose(r1)/1000., $
                      0, 0, $
                      xtitle='SQ1_FB/1000',ytitle='SQ2_FB/1000', errtitle='AD_Reading/1000', $
                      plot_titles=labels, errplot_titles=errlabels, col_start=columns[0], col_count=8


; Discover locking points

target_half_point_ch_by_ch=lonarr(8)
fb_half_point_ch_by_ch=lonarr(8)
SQ1_target=lonarr(8)
SQ1_feedback=lonarr(8)
deriv_fb1=fb1
sq1_v_phi=fb1
				
for chan=0,7 do begin	;calculate the derivatives of the V-phi plots
	deriv_fb1(*,chan)=smooth(deriv(input_sweep(*),fb1(*,chan)),20)
	sq1_v_phi(*,chan)=smooth(fb1(*,chan),20)
endfor

print,''
print,'###########################################################################'
print,'SQ1 bias, and SQ2 fb channel by channel:'
print,'###########################################################################'
print,' Channel Source_row       Target@half  sq1_fb@half '
print,'---------------------------------------------------'

; start should be at least 1 phi0 from right edge; margin should be
; between 0.1 (away from low derivative area) and at most 0.4
; (don't want to miss the max!).
start = 150
margin = 25
nfb   = ramp_count
for chan=0,7 do begin
	
		if slope lt 0 then begin
                	min_point=min(sq1_v_phi(start:nfb-1,chan),ind_min)
			ind_min=start+ind_min
	                ind_pos_der=where(deriv_fb1(0:ind_min-margin,chan) gt 0)
	                if n_elements(ind_pos_der) eq 1 then ind_pos_der=1
	                ind_max=max(ind_pos_der)
                endif else begin
                        max_point=max(sq1_v_phi(start:nfb-1,chan),ind_max)
                        ind_max=start+ind_max
                        ind_neg_der=where(deriv_fb1(0:ind_max-margin,chan) lt 0)
                        if n_elements(ind_neg_der) eq 1 then ind_neg_der=1
                        ind_min=max(ind_neg_der)
                endelse

		;remove comment here
		;ind_half_point=round((ind_min+ind_max)/2)
		
;		;comment from here
		midpoint=round((sq1_v_phi(ind_min,chan)+sq1_v_phi(ind_max,chan))/2.)
		vphi=sq1_v_phi(min([ind_min,ind_max]):max([ind_min,ind_max]),chan)
		ind_half_point=where(abs(vphi-midpoint) eq min(abs(vphi-midpoint)))
		ind_half_point=min([ind_min,ind_max])+ind_half_point
		;print,ind_half_point
		ind_half_point=ind_half_point(0)
;		;to here
;stop

		target_half_point_ch_by_ch(chan)=round(fb1(ind_half_point,chan))
		fb_half_point_ch_by_ch(chan)=round(1000.*input_sweep(ind_half_point))

                print,format='(i4, i10, i21, i12)',chan, lock_rows(chan+(rc-1)*8), $
                  target_half_point_ch_by_ch(chan), fb_half_point_ch_by_ch(chan)

endfor

SQ1_target=target_half_point_ch_by_ch
SQ1_feedback=fb_half_point_ch_by_ch

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

file_name_sq1_points=file_name+'_sq1_points'
plot_file = base_folder+'analysis/' + file_name_sq1_points + '.ps'
print,' '
print,'###########################################################################'
print,' '
print,'To view the SQ1 locking points check '
print,string(plot_file)
print,' '
print,'###########################################################################'
charsz=1

labels = string([columns, rows], format='("Feed Back, SQ2 Column ",I2," Row ",I2)')
auto_setup_plot_servo,plot_file, $
                      input_sweep, transpose(fb1)/1000., 0, $
                      SQ1_feedback/1000., SQ1_target/1000., /points, $
                      xtitle='SQ1_FB/1000',ytitle='SQ2_FB/1000', $
                      plot_titles=labels, col_start=columns[0], col_count=8

if keyword_set(poster) then begin
   f = strsplit(plot_file,'/',/extract)
   auto_post_plot,poster,filename=f[n_elements(f)-1]
endif

end 
