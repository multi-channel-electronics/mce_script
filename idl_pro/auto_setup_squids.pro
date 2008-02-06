pro auto_setup_squids, COLUMN=column, ROW=row,RCs=rcs,interactive=interactive,text=text,numrows=numrows,note=note,ramp_sa_bias=ramp_sa_bias,check_bias=check_bias,short=short

; Aug. 21, 2006, created by Elia Battistelli (EB)
;

;----------------------------------------------------------------------------------------------------------
;PRELIMINARY PROCEDURES: set the RC if not set among the rest
;----------------------------------------------------------------------------------------------------------


step1:

;COMUNICATION:
print,''
print,'##########################################################################################'
print,'#1) The first step is to set data acquisition variables and other preliminary procedures #'
print,'##########################################################################################'
print,''

;CLOSE ALL OPEN FILES. IT HELPS AVOID ERRORS 
close,/all
status=0

;set_directory CREATES FOLDERS AND FILES WHERE TO STORE THE TUNING DATA AND PLOTS
if not keyword_set(short) then spawn,'set_directory' 

;LET'S DEFINE FILENAMES AND FOLDERS
current_data = ''							;current_data: the today's date folder
openr, 3, '/data/cryo/current_data_name'	
readf, 3, current_data							;the date
close,3
todays_folder = '/data/cryo/' + current_data + '/'			;the folder
config_mce_file=todays_folder+'config_mce_auto_setup_'+current_data	;the config file

; Load the experiment config; this is what we update at each stage.
exp_config_file=todays_folder+'experiment.cfg'
load_exp_params,exp_config_file,exp_config

time=systime(1,/utc)							;c time
file_folder=string(time,format='(i10)')					;c time in a string
spawn,'mkdir '+todays_folder+file_folder				;folder where to store all the data files
spawn,'mkdir '+todays_folder+'analysis/'+file_folder			;folder where to store all the plots
c_filename=file_folder+'/'+file_folder

;DEFAULT read-out CARD
if not keyword_set(RCs) then begin
        print,'WARNING: you have not specified the read-out card number so I will set all RCs!'
        RCs=[1,2,3,4]
endif
rc_enable=intarr(4)
rc_enable(rcs(*)-1)=1

;CHECK WHETHER THE SSA and SQ2 BIAS HAVE ALREADY BEEN SWITCHED ON
on_bias=0
if keyword_set(check_bias) then begin
	for jj=0,n_elements(RCs)-1 do begin
	        RC=RCs(jj)
	        on_sabias=1
		spawn,'check_zero rc'+strcompress(string(RC),/remove_all)+' sa_bias >> '+todays_folder+c_filename+'.log',exit_status=on_sabias
		on_sabias=abs(on_sabias-1)
		on_bias=on_bias+on_sabias
	endfor
endif
on_sq2bias=1
spawn,'check_zero bc3 flux_fb >> '+todays_folder+c_filename+'.log',exit_status=on_sq2bias
on_sq2bias=abs(on_sq2bias-1)
on_bias=on_bias+on_sq2bias

;SET DATA FORMAT, CLEAR COMUNICATIONS AND RESET THE MCE
print, 'mce_reset_clean suppressed!'
;spawn,'mce_reset_clean >> '+todays_folder+c_filename+'.log'
;spawn,'clear_fifo_mce_reply >> '+todays_folder+c_filename+'.log'

;ENTER HERE THE VALUES RELATED TO YOUR CAMERA
samp_num=10							;number of data coadded
if not keyword_set(numrows) then numrows=33			;number of rows
good_squid_amplitude = 5000					;the program recommends turning a SQUID off if its V-phi is smaller than this

;!MFH - source from exp_config.

; normtbias1=65000   	;35000					;for the 3 detector bias configuration this is the bias at which the TES go normal
; normtbias2=65000        ;35000
; normtbias3=65000    	;35000
; normbias_time = 0.1						;how long should they be normal

; tbias1=0	;3000						;end detectors bias
; tbias2=0	;3000	
; tbias3=0	;3000	

tbias1     = exp_config.tes_bias_bc1
tbias2     = exp_config.tes_bias_bc2
tbias3     = exp_config.tes_bias_bc3
normtbias1 = exp_config.tes_bias_bc1_normal
normtbias2 = exp_config.tes_bias_bc2_normal
normtbias3 = exp_config.tes_bias_bc3_normal
normbias_time = exp_config.tes_bias_normal_time

;pidp=0								;pid parameters
;pidi=-40		

pidp = exp_config.servo_p
pidi = exp_config.servo_i
;!

final_data_mode=2						;Mode to set in the config file after all data is acquired.
ramp_sq1_bias_run=0						;Set this to 1 to sweep the tes bias and look at squid v-phi response.

sq2slope=-1							;it changes the sq1 and sq2 servos imposing them to lock on positive or negative slopes
sq1slope=-1

SA_feedback_file=lon64arr(32)
SA_feedback_file(*)=32000

SQ2_feedback_file=lon64arr(32)
SQ2_feedback_file(*)=8200

if n_elements(ROW) eq 0 then begin				;row used in the last frametest plot
	print,'Row = 0 is used for frametest_plot by default!'
	ROW=2
endif


;DETECTOR BIAS
;Setting detectors bias by first driving them normal and then to the transition.
;Here we specify three different detector bias corresponding to 3 different groups of detectors
spawn,'bias_tess '+strtrim(normtbias1,1)+' '+strtrim(normtbias2,1)+' '+strtrim(normtbias3,1) 
wait,normbias_time
spawn,'bias_tess '+strtrim(tbias1,1)+' '+strtrim(tbias2,1)+' '+strtrim(tbias3,1)

;!MFH!
; WRITING INTO THE CONFIG FILE
; openu,1,config_mce_file
; line=''
; repeat readf,1,line until strmid(line,0,11) eq "#Setting RC"
; for i=0,3 do begin
; 	writeu,1,'set RC'+strcompress(string(i+1),/remove_all)+'   ='+string(rc_enable(i))+' #'
; 	readf,1,line
; endfor
; repeat readf,1,line until strmid(line,0,19) eq "#Setting sample_num"
; writeu,1,'set sample_num   ='+string(samp_num)+' #'
; repeat readf,1,line until strmid(line,0,17) eq "#Setting tes_bias"
; set_tes_bias='set tes_bias_bc1 = '+string(tbias1)
; writeu,1,set_tes_bias+' #'
; readf,1,line
; set_tes_bias='set tes_bias_bc2 = '+string(tbias2)
; writeu,1,set_tes_bias+' #'
; readf,1,line
; set_tes_bias='set tes_bias_bc3 = '+string(tbias3)
; writeu,1,set_tes_bias+' #'
; close, 1

exp_config.config_rc = rc_enable
exp_config.sample_num = samp_num
;; These are read from exp_config, not written (unless necessary)
; exp_config.tes_bias_bc1 = tbias1
; exp_config.tes_bias_bc2 = tbias2
; exp_config.tes_bias_bc3 = tbias3


;THE SQUIDS BIAS CAN BE SPECIFIED APRIORI AND READ FROM A FILE
def_sa_bias = lon64arr(32)
sq2_bias = lon64arr(32)
sq1_bias = lon64arr(41)

openu,10,todays_folder+'/sabias.init'				;SSA bias
for cols=0,31 do begin
	readf,10,line
	def_sa_bias(cols)=float(line)
endfor
close,10

openu,15,todays_folder+'/sq2bias.init'				;SQ2 bias
for cols=0,31 do begin
        readf,15,line
        sq2_bias(cols)=float(line)
endfor
close,15

openu,17,todays_folder+'/sq1bias.init'				;SQ1 bias
for rows=0,40 do begin
        readf,17,line
        sq1_bias(rows)=float(line)
endfor
close,17

;!MFH!

; for jj=0,n_elements(RCs)-1 do begin
;         RC=RCs(jj)
;         openu,1,config_mce_file
;         line=''
;         repeat readf,1,line until strmid(line,0,20) eq '#Setting SA bias '+strcompress('RC'+string(RC),/remove_all)
;         for j=0,7 do begin
;                 set_bias='set '+strcompress('sa_bias'+string(j+8*(RC-1)),/remove_all)+'   = '+strcompress(string(def_sa_bias(j+8*(RC-1))),/remove_all)
;                 writeu,1,set_bias+' #'
;                 readf,1,line
;         endfor
;         repeat readf,1,line until strmid(line,0,21) eq '#Setting sq2 bias '+strcompress('RC'+string(RC),/remove_all)
;         for j=0,7 do begin
;                 set_sq2_bias='set '+strcompress('sq2bias'+string(j+8*(RC-1)),/remove_all)+'     = '+strcompress(string(sq2_bias(j+8*(RC-1))),/remove_all)
;                 writeu,1,set_sq2_bias+' #'
;                 readf,1,line
;         endfor
;         close,1
; endfor

exp_config.sa_bias = def_sa_bias
exp_config.sq2_bias = sq2_bias

;!MFH
; ;INITIALIZE THE adc_offset CONFIG FILE
column_adc_offset=lon64arr(32)

; Save experiment params, make config script, run it.
save_exp_params,exp_config,exp_config_file

;RUN THE config FILE
; spawn,'mce_make_config',exit_status=status1
; if status1 eq 0 then begin
;     spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status1
; endif
;!MFH
mce_make_config, params_file=exp_config_file, $
  filename=config_mce_file, $
  $ ;logfile=todays_folder+c_filename+'.log', $
  /run_now, exit_status=status1

if status1 ne 0 then begin
	print,''
	print,'#####################################################################################'
	print,'# ERROR! AN ERROR HAS OCCURED RUNNING THE CONFIG FILE ON THE PRELIMINARY PROCEDURES #'
	print,'#####################################################################################'
	print,''
	exit,status=1	
endif

;IF THE SSA AND SQ2 BIAS WERE PREVIOUSLY OFF THE SYSTEM WAITS FOR TERMALIZATION
if keyword_set(check_bias) then begin
	if on_bias eq 0 then begin
		print,''
		print,'#########################################################'
		print,'# THE SSA AND SQ2 BIAS WERE FOUND OFF SO I TURN THEM ON #' 
		print,'# AND I WAIT A COUPLE OF MINUTES TO WARM UP THE SYSTEM! #'
		print,'#########################################################'
		print,''
		wait,210
	endif
endif

;WRITES A NOTE FILE
if keyword_set(note) then begin
	openw,20,todays_folder+c_filename+'_note'
	printf,20,'#Note entered with SQUID autotuning data acquisition'
	printf,20,note
	close,20
endif

;INITIALIZE THE SQUID TUNING RESULTS FILE
header_file=todays_folder+c_filename+'.sqtune'
openw,20,header_file
printf,20,'<SQUID>'
printf,20,'<SQ_tuning_completed> 0'
printf,20,'<SQ_tuning_date> '+current_data
printf,20,'<SQ_tuning_dir> '+string(time,format='(i10)')
printf,20,'</SQUID>'
close,20
                                                                                                                   
spawn,'rm -f /data/cryo/last_squid_tune'
spawn,'ln -s '+todays_folder+c_filename+'.sqtune /data/cryo/last_squid_tune'

;#######STARTS THE CYCLE OVER THE 4 RCs TO SET ALL THE BIAS AND FB#######

for jj=0,n_elements(RCs)-1 do begin

	RC=RCs(jj)
        RC_indices = 8*(RC-1) + indgen(8)

        print,''
        print,'#################################################################'
        print,'#            NOW SETTING COLUMNS OF READ-OUT CARD '+strcompress(string(RC),/remove_all)+'             #'
        print,'#################################################################'
        print,''

	if keyword_set(short) then begin			;if we don't find the column adc_offset we read them for the config file
;!MFH
; 		openu,1,config_mce_file
; 		line=''
;         	repeat readf,1,line until strmid(line,0,23) eq '#Setting adc_offset '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			readf,1,line
;         		off=strsplit(line,/extract)
; 			column_adc_offset(j+8*(RC-1))=fix(off(3))
; 		endfor
; 		close,1

                column_adc_offset(RC_indices) = exp_config.adc_offset_c(RC_indices)

		if short eq 1 then goto, step4 else goto, step5
	endif

	;----------------------------------------------------------------------------------------------------------
	;SA setup: ramps the SA bias together with the fb and finds the best SA bias' and offsets channel by channel
	;----------------------------------------------------------------------------------------------------------
	
	step2:
	
        timessa=systime(1,/utc)
        strtimessa=string(timessa,format='(i10)')
        ssa_file_name=strcompress(file_folder+'/'+strtimessa+'_RC'+string(RC),/remove_all)

	if keyword_set(interactive) then begin
		i1=dialog_message(['After some preliminary procedures (step 1), the auto_setup',$ 
				   'program is going to find the SSA bias and offsets',$ 
				   'for the columns of RC'+strcompress(string(RC),/remove_all)+' (step 2)!',$
				   ' ','CONTINUE?',' ',$
				   'If you have already set the SSA, answer no, and',$
		 		   'you will be redirected to the SQ2 setup (step 3).'], /QUESTION)	
		if i1 eq 'No' then goto, step3
	endif else begin
		i1='Yes'
	endelse
	

;!MFH - IS THIS NECESSARY!?
; 	;BEFORE STARTING THE SA SETUP WE HAVE TO RESET TO THE INITIAL VALUES ALL THE SETTINGS
; 	openu,1,config_mce_file
; 	line=''
; 	repeat readf,1,line until strmid(line,0,18) eq "#Setting data_mode"
; 	writeu,1,'set data_mode    = 0 #'
; 	repeat readf,1,line until strmid(line,0,19) eq "#Setting servo_mode"
; 	writeu,1,'set servo_mode   = 1 #'

	;repeat readf,1,line until strmid(line,0,20) eq '#Setting SA bias '+strcompress('RC'+string(RC),/remove_all)
	;for j=0,7 do begin
	;	set_bias='set '+strcompress('sa_bias'+string(j+8*(RC-1)),/remove_all)+'   = 0'
	;	writeu,1,set_bias+' #'
	;	readf,1,line
	;endfor
	;repeat readf,1,line until strmid(line,0,22) eq '#Setting SA offset '+strcompress('RC'+string(RC),/remove_all)
	;for j=0,7 do begin
	;	set_offset='set '+strcompress('sa_offset'+string(j+8*(RC-1)),/remove_all)+'   = 0'
	;	writeu,1,set_offset+' #'
	;	readf,1,line
	;endfor


; 	repeat readf,1,line until strmid(line,0,23) eq '#Setting adc_offset '+strcompress('RC'+string(RC),/remove_all)
; 	for j=0,7 do begin
; 		set_adcoffset='set '+strcompress('adc_offset'+string(j+8*(RC-1)),/remove_all)+'   = 0'
; 		writeu,1,set_adcoffset+' #'
; 		readf,1,line
; 	endfor
;         repeat readf,1,line until strmid(line,0,21) eq '#Setting sq2 bias '+strcompress('RC'+string(RC),/remove_all)
;         for j=0,7 do begin
;                 set_sq2_bias='set '+strcompress('sq2bias'+string(j+8*(RC-1)),/remove_all)+'     = 0 #'
;                 writeu,1,set_sq2_bias+' #'
;                 readf,1,line
;         endfor

        exp_config.data_mode = 0
        exp_config.servo_mode = 1
        exp_config.config_adc_offset_all = 0      ; configure one adc_offset for the whole column
        exp_config.adc_offset_c(RC_indices) = 0
        exp_config.sq2_bias(RC_indices) = 0
	
; 	close,1
	
	common ramp_sa_var,plot_file,final_sa_bias_ch_by_ch,SA_target,SA_fb_init,peak_to_peak

	if keyword_set(ramp_sa_bias) then begin				;if we want to fine the SSA bias again

                save_exp_params,exp_config,exp_config_file

                mce_make_config, params_file=exp_config_file, $
                  filename=config_mce_file, $
                  $        ;logfile=todays_folder+c_filename+'.log', $
                  /run_now, exit_status=status2

                ; spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status2
		if status2 ne 0 then begin
        		print,''
        		print,'######################################################################'
        		print,'# ERROR! AN ERROR HAS OCCURED JUST BEFORE RUNNING THE RAMP_SA SCRIPT #'
        		print,'######################################################################'
        		print,''
        		exit,status=2
		endif
		
		auto_setup_ramp_sa_fb_plot,ssa_file_name,RC=rc,interactive=interactive 
	
		if keyword_set(interactive) then begin
			i2=dialog_message(['The auto_setup has found the bias and the offsets',$
					   'reported in the plots for the 8 SSA of RC'+strcompress(string(RC),/remove_all)+' !',$
					   ' ','DO YOU WANT TO CHANGE THEM?'], /QUESTION)
			if i2 eq 'No' then begin
				i3=dialog_message(['Are you happy with the previous values',$
					   'and you want to proceed setting up the array?'], /QUESTION)
	       	         	if i3 eq 'No' then begin
					i3=dialog_message(['The auto_setup_program was terminated'])
					goto, theend
				endif else begin	
					goto, step3
				endelse
			endif
		endif

;!MFH	
; 		openu,1,config_mce_file
; 		line=''
; 		repeat readf,1,line until strmid(line,0,20) eq '#Setting SA bias '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			set_bias='set '+strcompress('sa_bias'+string(j+8*(RC-1)),/remove_all)+'   = '+strcompress(string(final_sa_bias_ch_by_ch(j)),/REMOVE_ALL)
; 			writeu,1,set_bias+' #'
; 			readf,1,line
; 		endfor
               
                exp_config.sa_bias(RC_indices) = final_sa_bias_ch_by_ch

 		;Divide by 2 when using the new type of readout card with the 1S40 FPGA. It also depends on the cable resistance. 
; 		;sa_offset_MCE2=floor(final_sa_bias_ch_by_ch/3) 
; 		sa_offset_MCE2=floor(final_sa_bias_ch_by_ch/2)
; 		;sa_offset_MCE2=floor(final_sa_bias_ch_by_ch*5./12)
                sa_offset_MCE2=floor(final_sa_bias_ch_by_ch * exp_config.sa_offset_bias_ratio)

;!MFH	
; 		repeat readf,1,line until strmid(line,0,22) eq '#Setting SA offset '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			set_offset='set '+strcompress('sa_offset'+string(j+8*(RC-1)),/remove_all)+'   = '+strcompress(string(sa_offset_MCE2(j)),/REMOVE_ALL)
; 			writeu,1,set_offset+' #'
; 			readf,1,line
; 		endfor

                exp_config.sa_offset(RC_indices) = sa_offset_MCE2

;!MFH	
; 		repeat readf,1,line until strmid(line,0,23) eq '#Setting adc_offset '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			set_adcoffset='set '+strcompress('adc_offset'+string(j+8*(RC-1)),/remove_all)+'   = '+strcompress(string(SA_target(j)),/REMOVE_ALL)
; 			writeu,1,set_adcoffset+' #'
; 			readf,1,line
; 		endfor
; 		close,1

                exp_config.config_adc_offset_all = 0
                exp_config.adc_offset_c(RC_indices) = SA_target
	        
;!MFH
; 		for j=0,7 do column_adc_offset(j+8*(RC-1))=SA_target(j)
                column_adc_offset(RC_indices) = SA_target

        	;repeat readf,1,line until strmid(line,0,21) eq '#Setting sq2 bias '+strcompress('RC'+string(RC),/remove_all)
        	;for j=0,7 do begin
        	;        set_sq2_bias='set '+strcompress('sq2bias'+string(j+8*(RC-1)),/remove_all)+'     = '+strcompress(string(sq2_bias(j+8*(RC-1))),/remove_all)
        	;        writeu,1,set_sq2_bias+' #'
        	;        readf,1,line
        	;endfor
                ;; MFH - the sq2_bias set here is commented out in Elia's latest code!
                ;exp_config.sq2_bias(RC_indices) = sq2_bias(RC_indices)

	endif else begin

		;Instead of ramping the SA bias, just use the default values, and ramp the SA fb to confirm that the v-phi's look good.

;!MFH
; 		openu,1,config_mce_file
; 		line=''
; 		repeat readf,1,line until strmid(line,0,20) eq '#Setting SA bias '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			set_bias='set '+strcompress('sa_bias'+string(j+8*(RC-1)),/remove_all)+'   = '+strtrim(def_sa_bias(j+(RC-1)*8),1)
; 			writeu,1,set_bias+' #'
; 			readf,1,line
; 		endfor

                exp_config.sa_bias(RC_indices) = def_sa_bias(RC_indices)
	
;		;sa_offset_MCE2=floor(def_sa_bias*5./12)  
;		sa_offset_MCE2=floor(def_sa_bias/2.)
                sa_offset_MCE2=floor(def_sa_bias * exp_config.sa_offset_bias_ratio)

;!MFH	
; 		repeat readf,1,line until strmid(line,0,22) eq '#Setting SA offset '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			set_offset='set '+strcompress('sa_offset'+string(j+8*(RC-1)),/remove_all)+'   = '+strtrim(sa_offset_MCE2(j+(RC-1)*8),1)
; 			writeu,1,set_offset+' #'
; 			readf,1,line
; 		endfor
                
                exp_config.sa_offset(RC_indices) = sa_offset_MCE2(RC_indices)
                
; 		close,1

;!MFH
                save_exp_params,exp_config,exp_config_file
                mce_make_config, params_file=exp_config_file, $
                  filename=config_mce_file, $
                  $        ;logfile=todays_folder+c_filename+'.log', $
                  /run_now, exit_status=status3

;                 spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status3
                if status3 ne 0 then begin
                        print,''
                        print,'######################################################################'
                        print,'# ERROR! AN ERROR HAS OCCURED JUST BEFORE RUNNING THE RAMP_SA SCRIPT #'
                        print,'######################################################################'
                        print,''
                        exit,status=3
                endif

		auto_setup_ramp_sa_fb_plot_const_bias,ssa_file_name,RC=rc,interactive=interactive 

; 		openu,1,config_mce_file
; 		repeat readf,1,line until strmid(line,0,23) eq '#Setting adc_offset '+strcompress('RC'+string(RC),/remove_all)
; 		for j=0,7 do begin
; 			set_adcoffset='set '+strcompress('adc_offset'+string(j+8*(RC-1)),/remove_all)+'   = '+strcompress(string(SA_target(j)),/REMOVE_ALL)
; 			writeu,1,set_adcoffset+' #'
; 			readf,1,line
; 		endfor
; 		close,1

                exp_config.config_adc_offset_all = 0
                exp_config.adc_offset_c(RC_indices) = SA_target

; 		for j=0,7 do column_adc_offset(j+8*(RC-1))=SA_target(j)
                column_adc_offset(RC_indices) = SA_target

	endelse
	
        save_exp_params,exp_config,exp_config_file
        ;!MFH
        ;spawn,config_mce_file + ' >>
        ;'+todays_folder+c_filename+'.log',exit_status=status5

        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status5
        if status5 ne 0 then begin
                print,''                        
                print,'################################################################'                        
		print,'# ERROR! AN ERROR HAS OCCURED AFTER RUNNING THE RAMP_SA SCRIPT #'
                print,'################################################################'                        
		print,''
                exit,status=5
        endif
	
	;stop
	
	;----------------------------------------------------------------------------------------------------------
	;SQ2 setup: 
	;----------------------------------------------------------------------------------------------------------
	
	step3:
	
	if keyword_set(interactive) then begin
		if i1 eq 'Yes' then begin
			i4=dialog_message(['The auto_setup program will go on by',$
					   'running the SQ2 servo to determine',$
					   'the SSA fb and the SQ2 bias',$ 
					   'for the columns of RC'+strcompress(string(RC),/remove_all)+' (step 3)!',$
					   ' ','CONTINUE?',' ',$
					   'If you have already set the SQ2 bias',$
					   'and the SSA fb, answer no, and you will',$
		 			   'be redirected to the SQ1 setup (step 4).'], /QUESTION)
	
			if i4 eq 'No' then goto, step4
		endif else begin
			i4=dialog_message(['The auto_setup program will go on by',$
					   'running the SQ2 servo to determine',$
					   'the SSA fb and the SQ2 bias',$
				           'for the columns of RC'+strcompress(string(RC),/remove_all)+' (step 3)!',$
					   '',$
					   'NOTE: since you have chosen not to run the',$
					   'SSA setup (jump step 2), the initial SA fb for',$
					   'the SQ2 servo will be an arbitrary ',$
					   'mid range of 32000',$
					   ' ','CONTINUE?',' ',$
					   'If you have already set the SQ2 bias',$
					   'and the SSA fb, answer no, and you will',$
		 			   'be redirected to the SQ1 setup (step 4).'], /QUESTION)
	
			if i4 eq 'No' then goto, step4
			        spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status6
        			if status6 ne 0 then begin
                			print,''
                			print,'##################################################################'
                			print,'# ERROR! AN ERROR HAS OCCURED BEFORE RUNNING THE SQ2SERVO SCRIPT #'
                			print,'##################################################################'
                			print,''
                			exit,status=6
        			endif
			SA_fb_init=lon64arr(8)
			SA_fb_init(*)=32000
		endelse
	endif else begin
	        i4='Yes'
	endelse
	
	common sq2_servo_var,SQ2_target,SQ2_feedback,file_out
	
	;BEFORE STARTING THE SQ2 SETUP WE HAVE TO RESET TO THE INITIAL VALUES ALL THE SETTINGS
	;sq2_bias_vec=replicate(sq2_bias,8)

; 	openu,1,config_mce_file
; 	line=''
; 	repeat readf,1,line until strmid(line,0,18) eq "#Setting data_mode"
; 	writeu,1,'set data_mode    = 0 #'
; 	repeat readf,1,line until strmid(line,0,19) eq "#Setting servo_mode"
; 	writeu,1,'set servo_mode   = 1 #'
; 	; We need to turn the sq2 biases back on after sa tuning.
; 	repeat readf,1,line until strmid(line,0,21) eq '#Setting sq2 bias '+strcompress('RC'+string(RC),/remove_all)
; ;	for j=0,7 do begin
; 		set_sq2_bias='set '+strcompress('sq2bias'+string(j+8*(RC-1)),/remove_all)+'     = '+strtrim(sq2_bias(j+8*(RC-1)),1)+' #'
; 		writeu,1,set_sq2_bias+' #'
; 		readf,1,line
; 	endfor
        
        exp_config.data_mode = 0
        exp_config.servo_mode = 1
        exp_config.sq2_bias(RC_indices) = sq2_bias(RC_indices)

	;repeat readf,1,line until strmid(line,0,23) eq '#Setting sa fb '+strcompress('RC'+string(RC),/remove_all)
	;for j=0,7 do begin
	;	set_safb='set '+strcompress('safb'+string(j+8*(RC-1)),/remove_all)+'        = 0'
	;	writeu,1,set_safb+' #'
	;	readf,1,line
	;endfor
	
; 	repeat readf,1,line until strmid(line,0,17) eq "#Setting sq1 bias"
;         for i=0,40 do begin
;                 set_sq1bias='set '+strcompress('sq1bias'+string(i),/remove_all)+'        = '+strcompress(string(sq1_bias(i)),/REMOVE_ALL)
;                 writeu,1,set_sq1bias+' #'
;                 readf,1,line
;         endfor
; 	close,1

        exp_config.sq1_bias = sq1_bias

        ;!MFH
	;spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status6
        
        save_exp_params,exp_config,exp_config_file
        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status6

        if status6 ne 0 then begin
                print,''
                print,'##################################################################'
                print,'# ERROR! AN ERROR HAS OCCURED BEFORE RUNNING THE SQ2SERVO SCRIPT #'
                print,'##################################################################'
                print,''
                exit,status=6
        endif

	
	;Sets the initial SA fb (found in the previous step or set to mid-range) for the SQ2 servo
	zero=(rc-1)*8
	;SA_feedback_file=lonarr(32)
	SA_feedback_file(*)=32000
	for i=zero,zero+7 do begin 
		SA_feedback_file(i)=SA_fb_init(i-zero)	
	endfor
	
	SA_feedback_string=''
	for i=0,31 do begin
		SA_feedback_string=SA_feedback_string+strcompress(string(SA_feedback_file(i))+'\n',/remove_all)
	endfor
	SA_feedback_string='echo -e "'+SA_feedback_string+'"> '+todays_folder+'safb.init'
	spawn,SA_feedback_string
	
	timesq2=systime(1,/utc)
        strtimesq2=string(timesq2,format='(i10)')
        sq2_file_name=strcompress(file_folder+'/'+strtimesq2+'_RC'+string(RC),/remove_all)

	auto_setup_sq2servo_plot,sq2_file_name,SQ2BIAS=SQ2_bias,RC=rc,interactive=interactive,slope=sq2slope,gain=exp_config.sq2servo_gain ;,/lockamp

	if keyword_set(interactive) then begin
		i5=dialog_message(['The auto_setup has found the RC'+strcompress(string(RC),/remove_all)+' SSA fb',$
				   'reported in the plots for the 8 ',$
				   'channels of the SQ2!',$
				   ' ','DO YOU WANT TO CHANGE THEM?'], /QUESTION)
		if i5 eq 'No' then begin
			i9=dialog_message(['Are you happy with the previous values',$
                                   'and you want to proceed setting up the array?'], /QUESTION)
			if i9 eq 'No' then begin
				i9=dialog_message(['The auto_setup_program was terminated'])
				goto, theend
			endif else begin
                                goto, step4
                        endelse
		endif
	endif
	
;!MFH
; 	openu,1,config_mce_file
; 	line=''
	
; 	repeat readf,1,line until strmid(line,0,23) eq '#Setting sa fb '+strcompress('RC'+string(RC),/remove_all)
; 	for j=0,7 do begin
; 		set_safb='set '+strcompress('safb'+string(j+8*(RC-1)),/remove_all)+'        = '+strcompress(string(sq2_target(j)),/REMOVE_ALL)
; 		writeu,1,set_safb+' #'
; 		readf,1,line
; 	endfor
; 	repeat readf,1,line until strmid(line,0,17) eq "#Setting sq1 bias"
; 	for i=0,40 do begin
; 		set_sq1bias='set '+strcompress('sq1bias'+string(i),/remove_all)+'        = '+strcompress(string(sq1_bias(i)),/REMOVE_ALL)
;                 writeu,1,set_sq1bias+' #'
;                 readf,1,line
; 	endfor
; 	close,1

        exp_config.sa_fb(RC_indices) = sq2_target
        exp_config.sq1_bias = sq1_bias

; 	spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status8
        save_exp_params,exp_config,exp_config_file
        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status8
        
        if status8 ne 0 then begin
                print,''
                print,'#################################################################'
                print,'# ERROR! AN ERROR HAS OCCURED AFTER RUNNING THE SQ2SERVO SCRIPT #'
                print,'#################################################################'
                print,''
                exit,status=8
        endif

	;----------------------------------------------------------------------------------------------------------
	;SQ1_servo: 
	;----------------------------------------------------------------------------------------------------------
	
	step4:
	
	if keyword_set(interactive) then begin
		if i4 eq 'Yes' then begin
			i6=dialog_message(['The auto_setup program will go on by',$
					   'running the SQ1 servo to determine',$
					   'the SQ2 fb and the SQ1 bias',$ 
					    'for the columns of RC'+strcompress(string(RC),/remove_all)+' (step 4)!',$
					   ' ','CONTINUE?',' ',$
					   'If you have already set the SQ1 bias',$
					   'and the SQ2 fb, answer no, and you will',$
		 			   'be redirected to the ramp SQ1 check (step 5).'], /QUESTION)
	
			if i6 eq 'No' then goto, step5
		endif else begin
			i6=dialog_message(['The auto_setup program will go on by',$
					   'running the SQ1 servo to determine',$
					   'the SQ2 fb and the SQ1 bias',$
					   'for the columns of RC'+strcompress(string(RC),/remove_all)+' (step 4)!',$
					   '',$
					   'NOTE: since you have chosen not to run the',$
					   'SQ2 setup (jump step 3), the initial SQ2 fb for',$
					   'the SQ1 servo will be an arbitrary ',$
					   'mid range of 32000',$
					   ' ','CONTINUE?',' ',$
					   'If you have already set the SQ1 bias',$
					   'and the SQ2 fb, answer no, and you will',$
		 			   'be redirected to the ramp SQ1 check (step 5).'], /QUESTION)
	
			if i6 eq 'No' then goto, step5
			spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status9
        		if status9 ne 0 then begin
                		print,''
                		print,'##################################################################'
                		print,'# ERROR! AN ERROR HAS OCCURED BEFORE RUNNING THE SQ1SERVO SCRIPT #'
                		print,'##################################################################'
                		print,''
                		exit,status=9
        		endif
			SQ2_feedback=lon64arr(8)
                        SQ2_feedback(*)=8200
			initial_sq2_fb=8200
		endelse
	endif else begin
	        i6='Yes'
	endelse
	if keyword_set(short) then begin
		SQ2_feedback=lon64arr(8)
                SQ2_feedback(*)=8200
                initial_sq2_fb=8200
	endif	

        SQ2_feedback=lon64arr(8)
        SQ2_feedback(*)=8200
        initial_sq2_fb=8200

	
	common sq1_servo_var,SQ1_target,SQ1_feedback,file_out2

;!MFH	
; 	;BEFORE STARTING THE SQ1 SETUP WE HAVE TO RESET TO THE INITIAL VALUES ALL THE SETTINGS
; 	openu,1,config_mce_file
; 	line=''
; 	repeat readf,1,line until strmid(line,0,18) eq "#Setting data_mode"
; 	writeu,1,'set data_mode    = 0 #'
; 	repeat readf,1,line until strmid(line,0,17) eq "#Setting num_rows"
; 	writeu,1,'set num_rows   = '+strtrim(numrows,1)+' #'
; 	readf,1,line
; 	writeu,1,'set num_rows_reported   = '+strtrim(numrows,1)+' #'
; 	repeat readf,1,line until strmid(line,0,19) eq "#Setting servo_mode"
; 	writeu,1,'set servo_mode   = 1 #'
		
; 	;repeat readf,1,line until strmid(line,0,19) eq '#Setting sq2 fb '+strcompress('RC'+string(RC),/remove_all)
; 	;for j=0,7 do begin
; 	;	set_sq2fb='set '+strcompress('sq2fb'+string(j+8*(RC-1)),/remove_all)+'        = 16000'	;PUT IT BACK TO ZERO WHEN YOU HAVE THE SQ1SERVO
; 	;	writeu,1,set_sq2fb+' #'
; 	;	readf,1,line
; 	;endfor
; 	repeat readf,1,line until strmid(line,0,12) eq "#Setting pid"
; 	writeu,1,'set p            = 0 #'
; 	readf,1,line
; 	writeu,1,'set i            = 0 #'
; 	readf,1,line
; 	writeu,1,'set d            = 0 #'
; 	readf,1,line
	
; 	close,1

        exp_config.data_mode = 0
        exp_config.num_rows = numrows
        exp_config.num_rows_reported = numrows
        exp_config.servo_mode = 1
        exp_config.servo_p = 0
        exp_config.servo_i = 0
        exp_config.servo_d = 0
	
; 	spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status9
        save_exp_params,exp_config,exp_config_file
        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status9
        if status9 ne 0 then begin
                print,''
                print,'##################################################################'
                print,'# ERROR! AN ERROR HAS OCCURED BEFORE RUNNING THE SQ1SERVO SCRIPT #'
                print,'##################################################################'
                print,''
                exit,status=9
        endif


	 ;Sets the initial SQ2 fb (found in the previous step or set to mid-range) for the SQ1 servo
	zero=(rc-1)*8
	;SQ2_feedback_file=intarr(32)
	;SQ2_feedback_file(*)=10000
	for i=zero,zero+7 do begin 
		SQ2_feedback_file(i)=SQ2_feedback(i-zero)	
	endfor
	
	SQ2_feedback_string=''
	for i=0,31 do begin
		SQ2_feedback_string=SQ2_feedback_string+strcompress(string(SQ2_feedback_file(i))+'\n',/remove_all)
	endfor
	SQ2_feedback_string='echo -e "'+SQ2_feedback_string+'" > '+todays_folder+'sq2fb.init'
	spawn,SQ2_feedback_string
       
	timesq1=systime(1,/utc)
        strtimesq1=string(timesq1,format='(i10)')


        if exp_config.config_fast_sq2 then begin

            print, 'Using biasing address card (bac) to sq1servo each row separately.'
            ; This block uses original sq1servo to get the full block of
            ; ramps for all rows.

            SQ2_feedback_full_array=lon64arr(numrows,8)

            for sq1servorow=0,numrows-1 do begin
                sq1_file_name=strcompress(file_folder+'/'+strtimesq1+'_RC'+string(RC)+'_row'+string(sq1servorow),/remove_all)
		;row=0

                ; Rewrite the row.init file, forcing all columns
                ; to this row.
                row_init_string=''
                for j=0,31 do begin
                        row_init_string=row_init_string+strcompress(string(sq1servorow)+'\n',/remove_all)
                endfor
                row_init_string='echo -e "'+row_init_string+'" > '+todays_folder+'row.init'
                spawn,row_init_string
  	
		auto_setup_sq1servo_plot, sq1_file_name,SQ1BIAS=sq1_bias(0),RC=rc, $
                  numrows=numrows,interactive=interactive,slope=sq1slope,sq2slope=sq2slope, $
                  gain=exp_config.sq1servo_gain,LOCK_ROWS=(lonarr(32) + sq1servorow)

                SQ2_feedback_full_array(sq1servorow,*)=sq1_target(*)

		if keyword_set(interactive) then begin
			i7=dialog_message(['The auto_setup has found the SQ2 fb',$
					   'reported in the plots for the 8 ',$
					   'channels of the SQ1 of RC'+strcompress(string(RC),/remove_all)+'!',$
					   ' ','DO YOU WANT TO CHANGE THEM?'], /QUESTION)
			if i7 eq 'No' then begin
				i8=dialog_message(['Are you happy with the previous values',$
                                	   'and you want to proceed setting up the array?'], /QUESTION)
                        	if i8 eq 'No' then begin
                                	i8=dialog_message(['The auto_setup_program was terminated'])
                                	goto, theend
				endif else begin
                                	goto, step5
                        	endelse
			endif
		endif
            endfor	

; MFH - save all sq2fb points
            for j=0,n_elements(RC_indices)-1 do begin
                sq2_rows = 41
                c_ofs = RC_indices(j)*sq2_rows
                exp_config.sq2_fb_set(c_ofs:(c_ofs+numrows-1)) = SQ2_feedback_full_array(*,j)
            endfor

            ; For single rowing; use the selected rows from sq2_param:
            for j=0,7 do begin
                sq1_target(j) = SQ2_feedback_full_array(exp_config.sq2_rows(RC_indices(j)),j)
            endfor


        endif else begin
            ; This block uses original sq1servo to
            ; lock on a specific row for each column
            
            ; Rewrite the row.init file using the exp_config information.
            row_init_string=''
            for j=0,31 do begin
                row_init_string=row_init_string+strcompress(string(exp_config.sq2_rows(j))+'\n',/remove_all)
            endfor
            row_init_string='echo -e "'+row_init_string+'" > '+todays_folder+'row.init'
            spawn,row_init_string

            sq1_file_name=strcompress(file_folder+'/'+strtimesq1+'_RC'+string(RC),/remove_all)
            
            auto_setup_sq1servo_plot, sq1_file_name,SQ1BIAS=sq1_bias(0), $
              RC=rc,numrows=numrows,interactive=interactive,slope=sq1slope,sq2slope=sq2slope, $
              gain=exp_config.sq1servo_gain,lock_rows=exp_config.sq2_rows

            if keyword_set(interactive) then begin
                i7=dialog_message(['The auto_setup has found the SQ2 fb',$
                                   'reported in the plots for the 8 ',$
                                   'channels of the SQ1 of RC'+strcompress(string(RC),/remove_all)+'!',$
                                   ' ','DO YOU WANT TO CHANGE THEM?'], /QUESTION)
                if i7 eq 'No' then begin
                    i8=dialog_message(['Are you happy with the previous values',$
                                       'and you want to proceed setting up the array?'], /QUESTION)
                    if i8 eq 'No' then begin
                        i8=dialog_message(['The auto_setup_program was terminated'])
                        goto, theend
                    endif else begin
                        goto, step5
                    endelse
                endif
            endif
            
        endelse
            
; done.

; Single row approach -- these will be ignored in the multi-variable case!

;!MFH
; 	openu,1,config_mce_file
; 	line=''
	
; 	repeat readf,1,line until strmid(line,0,19) eq '#Setting sq2 fb '+strcompress('RC'+string(RC),/remove_all)
; 	for j=0,7 do begin
; 		set_sq2fb='set '+strcompress('sq2fb'+string(j+8*(RC-1)),/remove_all)+'        = '+strcompress(string(sq1_target(j)),/REMOVE_ALL)
; 		writeu,1,set_sq2fb+' #'
; 		readf,1,line
; 	endfor
; 	close,1

        print,'sq1_target = ',string(sq1_target)
        exp_config.sq2_fb(RC_indices) = sq1_target
        save_exp_params,exp_config,exp_config_file
        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status11
; 	spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status11
        if status11 ne 0 then begin
                print,''
                print,'##################################################################'
                print,'# ERROR! AN ERROR HAS OCCURED AFTER RUNNING THE SQ1SERVO SCRIPT #'
                print,'##################################################################'
                print,''
                exit,status=11
        endif

	SQ2_feedback_string=''
	for i=0,31 do begin
		SQ2_feedback_string=SQ2_feedback_string+strcompress(string(sq1_target(i mod 8))+'\n',/remove_all)
	endfor
	SQ2_feedback_string='echo -e "'+SQ2_feedback_string+'"> '+todays_folder+'sq2fb.init'
	spawn,SQ2_feedback_string
		
	step5:
endfor

;----------------------------------------------------------------------------------------------------------
;SQ1 ramp check:
;----------------------------------------------------------------------------------------------------------

;!MFH - replaced with adc_offset_cr
; ;Generate adc_offset files which will contain the adc offset values for each individual detector.
; ;The adc_off_run_file is called and run by the config file
; openw,20,adc_off_run_file
; printf,20,'#!/bin/csh'
; close,20
; spawn,'echo -e "\n">>'+adc_off_run_file

new_adc_arr = strarr(32)
squid_p2p_arr = strarr(32)
squid_lockrange_arr = strarr(32)
squid_lockslopedn_arr = strarr(32)
squid_lockslopeup_arr = strarr(32)
squid_multilock_arr = strarr(32)
squid_off_rec_arr = strarr(32)

for jj=0,n_elements(RCs)-1 do begin

        RC=RCs(jj)
        RC_indices = (RC-1)*8 + indgen(8)

        print,''
        print,'############################################################################'
        print,'#            NOW SETTING SETTING ADC_OFFSET OF READ-OUT CARD '+strcompress(string(RC),/remove_all)+'             #'
        print,'############################################################################'
        print,''

	common ramp_sq1_var, new_adc_offset, squid_p2p, squid_lockrange, squid_lockslope, squid_multilock

; 	;BEFORE STARTING THE CHECK WE HAVE TO RESET TO THE INITIAL VALUES ALL THE SETTINGS
; 	openu,1,config_mce_file
; 	line=''

; 	repeat readf,1,line until strmid(line,0,18) eq "#Setting data_mode"
; 	writeu,1,'set data_mode    = 0 #'
	
; 	repeat readf,1,line until strmid(line,0,19) eq "#Setting servo_mode"
; 	writeu,1,'set servo_mode   = 1 #'
	
; 	repeat readf,1,line until strmid(line,0,12) eq "#Setting pid"
; 	writeu,1,'set p            = 0 #'
; 	readf,1,line
; 	writeu,1,'set i            = 0 #'
; 	readf,1,line
; 	writeu,1,'set d            = 0 #'
; 	readf,1,line
	
; 	close,1
        exp_config.data_mode = 0
        exp_config.servo_mode = 1
        exp_config.servo_p = 0
        exp_config.servo_i = 0
        exp_config.servo_d = 0

; 	spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status12

        save_exp_params,exp_config,exp_config_file
        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status12

        if status12 ne 0 then begin
                print,''
                print,'################################################################'
                print,'# ERROR! AN ERROR HAS OCCURED BEFORE RUNNING THE SQ1RAMP CHECK #'
                print,'################################################################'
                print,''
                exit,status=12
        endif

	timersq1=systime(1,/utc)
        strtimersq1=string(timersq1,format='(i10)')
        rsq1_file_name=strcompress(file_folder+'/'+strtimersq1+'_RC'+string(RC),/remove_all)
	rsq1_file_name=string(rsq1_file_name)+'_sq1ramp'

	auto_setup_ramp_sq1_fb_plot,rsq1_file_name,RC=rc,interactive=interactive,numrows=numrows
	i10='Yes'
        if keyword_set(interactive) then begin
                i10=dialog_message(['The auto_setup has found the the new',$
                                   'adc_offset of RC'+strcompress(string(RC),/remove_all)+'!',$
                                   ' ','DO YOU WANT TO CHANGE THEM?'], /QUESTION)
                if i10 eq 'No' then begin
                        i11=dialog_message(['Are you happy with the previous values',$
                                   'and you want to proceed setting up the array?'], /QUESTION)
                        if i11 eq 'No' then begin
                                i8=dialog_message(['The auto_setup_program was terminated'])
                                goto, theend
                        endif else begin
                                goto, step6
                        endelse
                endif
        endif

	line=''
	
	if rc eq rcs(0) then begin
		all_adc_offsets = fltarr(32,numrows)
		all_squid_p2p = fltarr(32,numrows)
		all_squid_lockrange = fltarr(32,numrows)
		all_squid_lockslope = fltarr(32,numrows,2)
		all_squid_multilock = fltarr(32,numrows)
	endif
	
	new_off=new_adc_offset
	for j=0,7 do begin
		new_off(j,*)=(new_adc_offset(j,*)+column_adc_offset(j+8*(RC-1)))/samp_num
		all_adc_offsets((rc-1)*8+j,*) = new_off(j,*)
		all_squid_p2p((rc-1)*8+j,*) = squid_p2p(j,*)
		all_squid_lockrange((rc-1)*8+j,*) = squid_lockrange(j,*)
		all_squid_lockslope((rc-1)*8+j,*,0) = squid_lockslope(j,*,0)
		all_squid_lockslope((rc-1)*8+j,*,1) = squid_lockslope(j,*,1)
		all_squid_multilock((rc-1)*8+j,*) = squid_multilock(j,*)	
	endfor

        if i10 eq 'Yes' then begin
        	for j=0,7 do begin
                	setting_new_adc='echo "wb rc'+strcompress(string(RC),/REMOVE_ALL)+' adc_offset'+strcompress(string(j),/REMOVE_ALL)
                	for i=0,numrows-1 do begin

;!MFH
;                         	setting_new_adc=setting_new_adc+' '+string(all_adc_offsets((rc-1)*8+j,i), format='(i11)')
                            exp_config.adc_offset_cr( ((rc-1)*8 + j)*exp_config.array_width + i ) = $
                              all_adc_offsets((rc-1)*8+j,i)

                        	new_adc_arr((rc-1)*8+j)=new_adc_arr((rc-1)*8+j)+' '+string(all_adc_offsets((rc-1)*8+j,i), format='(i6)')
                        	squid_p2p_arr((rc-1)*8+j)=squid_p2p_arr((rc-1)*8+j)+' '+string(all_squid_p2p((rc-1)*8+j,i), format='(i6)')
                                squid_lockrange_arr((rc-1)*8+j)=squid_lockrange_arr((rc-1)*8+j)+' '+string(all_squid_lockrange((rc-1)*8+j,i), format='(i6)')
                                squid_lockslopedn_arr((rc-1)*8+j)=squid_lockslopedn_arr((rc-1)*8+j)+' '+strcompress(string(all_squid_lockslope((rc-1)*8+j,i,0)),/REMOVE_ALL)
                                squid_lockslopeup_arr((rc-1)*8+j)=squid_lockslopeup_arr((rc-1)*8+j)+' '+strcompress(string(all_squid_lockslope((rc-1)*8+j,i,1)),/REMOVE_ALL)
                                squid_multilock_arr((rc-1)*8+j)=squid_multilock_arr((rc-1)*8+j)+' '+string(all_squid_multilock((rc-1)*8+j,i), format='(i2)')
                                if all_squid_lockrange((rc-1)*8+j,i) lt good_squid_amplitude then turn_sq_off = 1 else turn_sq_off = 0
                                squid_off_rec_arr((rc-1)*8+j)=squid_off_rec_arr((rc-1)*8+j)+' '+strtrim(turn_sq_off,1)
                            endfor
;!MFH
;                        spawn,'echo -e "'+setting_new_adc+'" '+'\n">>'+adc_off_run_file
      		endfor
            endif

;!MFH
        ; Turn on adc_offset config for all columns.
        exp_config.config_adc_offset_all = 1

        save_exp_params,exp_config,exp_config_file
        mce_make_config, params_file=exp_config_file, $
          filename=config_mce_file, $
          $                ;logfile=todays_folder+c_filename+'.log', $
          /run_now, exit_status=status14

; 	spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status14
        if status14 ne 0 then begin
                print,''
                print,'###############################################################'
                print,'# ERROR! AN ERROR HAS OCCURED AFTER RUNNING THE SQ1RAMP CHECK #'
                print,'###############################################################'
                print,''
                exit,status=14
        endif

	common ramp_sq1_var, new_adc_offset, squid_p2p, squid_lockrange, squid_lockslope, squid_multilock

	timersq1c=systime(1,/utc)
        strtimersq1c=string(timersq1c,format='(i10)')
        rsq1c_file_name=strcompress(file_folder+'/'+strtimersq1c+'_RC'+string(RC),/remove_all)
        rsq1c_file_name=string(rsq1c_file_name)+'_sq1rampc'
	auto_setup_ramp_sq1_fb_plot,rsq1c_file_name,RC=rc,interactive=interactive,numrows=numrows

	if ramp_sq1_bias_run eq 1 then begin
		spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status16
                if status16 ne 0 then begin
                        print,''
                        print,'##################################################################################'
                        print,'# ERROR! AN ERROR HAS OCCURED BEFORE SETTING THE NEW ADC_OFF AFTER RAMP_SQ1_BIAS #'
                        print,'##################################################################################'
                        print,''
                	exit,status=16
		endif

		timertb=systime(1,/utc)
		strtimertb=string(timertb,format='(i10)')        
		rtb_file_name=strcompress(file_folder+'/'+strtimertb+'_RC'+string(RC),/remove_all)
        	rtb_file_name=string(rtb_file_name)+'_sq1rampb'
		auto_setup_ramp_sq1_bias_plot,rtb_file_name,RC=rc,interactive=interactive,numrows=numrows
	endif

step6:

endfor

;----------------------------------------------------------------------------------------------------------
;Frametest check: 
;----------------------------------------------------------------------------------------------------------

;BEFORE STARTING THE CHECK WE HAVE TO RESET TO THE INITIAL VALUES ALL THE SETTINGS
; openu,1,config_mce_file
; line=''
; repeat readf,1,line until strmid(line,0,18) eq "#Setting data_mode"
; writeu,1,'set data_mode    = '+strtrim(final_data_mode,1)+' #'
; repeat readf,1,line until strmid(line,0,19) eq "#Setting servo_mode"
; writeu,1,'set servo_mode   = 3 #'
                                                                                            
; repeat readf,1,line until strmid(line,0,12) eq "#Setting pid"
; writeu,1,'set p            = '+strcompress(string(pidp),/REMOVE_ALL)+' #'
; readf,1,line
; writeu,1,'set i            = '+strcompress(string(pidi),/REMOVE_ALL)+' #'
; readf,1,line
; writeu,1,'set d            = 0 #'
; readf,1,line
; close,1

exp_config.data_mode = final_data_mode
exp_config.servo_mode = 3
exp_config.servo_p = pidp
exp_config.servo_i = pidi
exp_config.servo_d = 0

save_exp_params,exp_config,exp_config_file
mce_make_config, params_file=exp_config_file, $
  filename=config_mce_file, $
  $                        ;logfile=todays_folder+c_filename+'.log', $
  /run_now, exit_status=status17

; spawn,config_mce_file + ' >> '+todays_folder+c_filename+'.log',exit_status=status17
if status17 ne 0 then begin
	print,''
        print,'##############################################################'
        print,'# ERROR! AN ERROR HAS OCCURED BEFORE TAKING A SAMPLE OF DATA #'
        print,'##############################################################'
        print,''
        exit,status=17
endif

if n_elements(RCs) lt 4 then begin
	for jj=0,n_elements(RCs)-1 do begin
        	RC=RCs(jj)
                timelock=systime(1,/utc)
                strtimelock=string(timelock,format='(i10)')
                lock_file_name=strcompress(file_folder+'/'+strtimelock+'_RC'+string(RC),/remove_all)
                lock_file_name=string(lock_file_name)+'_lock'
		if keyword_set(text) then begin
			auto_setup_frametest_plot, COLUMN=column, ROW=row,RC=rc,lock_file_name,interactive=interactive
		endif else begin
			auto_setup_frametest_plot, COLUMN=column, ROW=row,RC=rc,lock_file_name,/BINARY,interactive=interactive
		endelse
		step10:
	endfor
endif else begin
        timelock=systime(1,/utc)
        strtimelock=string(timelock,format='(i10)')
        lock_file_name=strcompress(file_folder+'/'+strtimelock+'_RCs',/remove_all)
        lock_file_name=string(lock_file_name)+'_lock'
        RC=5
        if keyword_set(text) then begin
                auto_setup_frametest_plot, COLUMN=column, ROW=row,RC=rc,lock_file_name,interactive=interactive
        endif else begin
                auto_setup_frametest_plot, COLUMN=column, ROW=row,RC=rc,lock_file_name,/BINARY,interactive=interactive
        endelse
	step11:
endelse

;file_chmod, adc_off_run_file,/a_execute
;spawn,'cp -p '+adc_off_run_file+' '+todays_folder+c_filename+'_adc_offset_conf'
spawn,'cp -p '+config_mce_file+' '+todays_folder+c_filename+'_config_mce_auto_setup_'+current_data

header_file=todays_folder+c_filename+'.sqtune'
openw,20,header_file
printf,20,'<SQUID>'
printf,20,'<SQ_tuning_completed> 1'
printf,20,'<SQ_tuning_date> '+current_data
printf,20,'<SQ_tuning_dir> '+string(time,format='(i10)')
for j=0,31 do printf,20,'<Col'+strtrim(j,1)+'_squid_vphi_p2p> '+squid_p2p_arr(j)
for j=0,31 do printf,20,'<Col'+strtrim(j,1)+'_squid_lockrange> '+squid_lockrange_arr(j)
for j=0,31 do printf,20,'<Col'+strtrim(j,1)+'_squid_lockslope_down> '+squid_lockslopedn_arr(j)
for j=0,31 do printf,20,'<Col'+strtrim(j,1)+'_squid_lockslope_up> '+squid_lockslopeup_arr(j)
for j=0,31 do printf,20,'<Col'+strtrim(j,1)+'_squid_multilock> '+squid_multilock_arr(j)
for j=0,31 do printf,20,'<Col'+strtrim(j,1)+'_squid_off_recommendation> '+squid_off_rec_arr(j)
printf,20,'</SQUID>'
close,20
                                                                                                  
spawn,'rm -f /data/cryo/last_squid_tune'
spawn,'ln -s '+todays_folder+c_filename+'.sqtune /data/cryo/last_squid_tune' 
spawn,'echo "'+current_data+'" > /data/cryo/last_squid_tune_name'
spawn,'echo "'+string(time,format='(i10)')+'" >> /data/cryo/last_squid_tune_name'

print,''
print,'##########################################################'
print,'# Auto-tuning of SQUIDs completed in '+current_data+'/'+string(time,format='(i10)')+' #'
print,'##########################################################'
print,''
print,'#####################################################################'
print,'# Congratulations, you have tuned '+strcompress(string(n_elements(RCs)*(33*8+16)),/REMOVE_ALL)+' SQUIDs in '+strcompress(string((systime(1,/utc)-time)/60.),/remove_all)+' minutes! #'
print,'#####################################################################'
print,''

exit,status=99
;stop

theend:

end
