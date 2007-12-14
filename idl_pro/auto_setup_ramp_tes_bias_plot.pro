pro ramp_tes_bias_plot, file_name,NODASSCRIPT=nodasscript,RC=rc,TES_HEATER=tes_heater,$
              ENGUNITS=engunits,$
              FOLDER=folder, DATE=date, PLOT_FILE=plot_file, $
              ABS_PLOT_FILE= abs_plot_file, HELP = help


;Written by Elia Battistelli, EB
;adapted from ramp_sq1_plot
;
;14 August 2006  (EB)
;Modified to:
;-automatically run the shell script (keyword /nodasscript in 
;case one doesn't want to) 
;-runs a shell script which writes some MCE/firmware info in the data file
;-also some cosmetic changes.



close,/all


default_folder = '/data/cryo/'

default_date = 'current_data/'


;Specify folder to read from if not provided.
if not keyword_set(folder) then folder= default_folder


;Specify subfolder to read from if not provided.
if not keyword_set(date) then date= default_date


if keyword_set( help) then begin
print, '______________________________'
print, 'Procedure  RAMP_TES_BIAS_PLOT'
print, '______________________________'
print, ''
print, 'The input Parameters and Options are'
print, ''
print, 'file_name  for data.  Can be full name, or short name in default directory'
print, '/zero, /one, ..etc to plot only specified SA channel.'    
print, '/ALL  to plot all eight channels on one page'    
print, '/ERRORS  to plot error bars on all points'    
print, '/ENGUNITS  to convert from AD counts to mV and uA.'    
print, '/PLOT_FILE to name the output, instead of default'    
print, '/ABS_PLOT_FILE to specify output name including full tree.'    
print, '/DATE to specify other than default subdir for data. '
print, 'If you also want to run the das script you can type:'
print, 'pro ramp_tes_bias_plot,file_name,DASSCRIPT=1,RC=rc,TES_HEATER=tes_heater'    
print, 'NOTE: TES HEATER RAMP OPTION NOT YET ACTIVATED'    
print, ''    
print, '______________________________'
print, 'The default folder is ' , default_folder
print, '______________________________'              
print, ' The default date is ', default_date
print, '______________________________'


endif else begin

if n_elements(nodasscript) eq 0 then begin
  if not keyword_set(RC) then begin
    print,'If you want to run the shell script you should specify the read-out card number!!'
    goto, fine
  endif
  if not keyword_set(tes_heater) then begin
    spawn,'read_status'+' '+strcompress('rc'+ string(rc),/REMOVE_ALL)+' '+file_name
    spawn,'ramp_tes_bias '+file_name+' '+string(rc)
  endif else begin
    spawn,'read_status'+' '+strcompress('rc'+ string(rc),/REMOVE_ALL)+' '+file_name
    spawn,'ramp_tes_bias '+file_name+' '+string(rc)+' '+string(tes_heater)
  endelse
endif

cd = ''
;Set filename.
full_name=folder+date+file_name
openr, 3, '/data/cryo/current_data_name'
readf, 3,  cd
close, 3
name_label = '/data/cryo' + '/' + cd + '/' + file_name 

;__________________________________________________________________
; Modification to put out  files in default location.   8 april 2005 halpern
;Set output filename.

;if not keyword_set(plot_file) then plot_file = file_name + '_v_phi.ps'

if not keyword_set(abs_plot_file) then  begin

; Changed to conformm to current storage structure.
  if keyword_set(plot_file) then begin
       plot_file = folder + date + 'analysis/' + plot_file
   endif else begin
     plot_file = folder + date + 'analysis/' +file_name + '_sq1x41.ps'
   endelse
; End of change.

endif else begin
   plot_file = abs_plot_file
endelse

;__________________________________________________________________



;Set up factors and captions for engineering and AD units.
if keyword_set(engunits)  then begin
    

;Note:  Gains changed on 13 April 2005 to correspond to hardware.

    nsum = 48.                  ;Samples summed in firmware.
    gain = 2.*96.                 ;Gain on Readout Card before AD
    full_scale = 1100.          ;mV at DA
    
    v_factor = full_scale / ( nsum * gain * 2^13 )
    v_units = ' (mV)'
    
    RL = 5000.                 ;RL on Inst Back Plane  for SA FB Bias card
    admax= 65535.               ;DAC full scale
    mv2micro = 0.001  
    
    i_factor = full_scale/ (RL * admax * mv2micro)
    i_units = ' (uAmps)'
    
endif else begin
    
    v_factor = 1.
    v_units = ' (AD Units/1000)'
    i_factor = 1.
    i_units = ' (AD Units/1000)'
    
endelse

; Read in header from the data file

;header = read_sa_header(full_name)
;
;Returned values are 
;       header.card  = readout card slot in use
;       header.bias  =  8 number array of SA_biases
;       header_offset = 8 number array of RC offsets.
;

;Convert SA_bias to current.
vmax = 2500.  ; mV
RL  = 15000.  ; Ohms
full_scale = 65535.   ; Digital fs = 2^16 -1.
ma2uA      = 1000.    ; convert to microamperes

;sa_bias = header.bias * vmax * ma2uA  / ( RL* full_scale)
sa_bias = 0 * vmax * ma2uA  / ( RL* full_scale)


    
   !p.multi=[0,2,4]            ;Multiple plot parameters.
;     !p.multi=[0,8,41]       ; Not a really good idea.  MH
    !p.region=[0,0,0,0]         ;Plot region.
    
 
 ;  print, ' Trying fast read'

;readin=mce_fast_read(full_name)  ;Read in file.

;__________________________________________________________________
;modified to sweep the sq1_bias

;print,'Reading data from  ', full_name

readin=read_2d_ramp_tes(full_name)  ;Read in file

; Read labels, loop sizes, etc.

    horiz_label=readin.labels[2]
    vert_label = readin.labels[1]
    card = readin.labels[0]
   
    n_heater = readin.specs[0]
    heater_start = readin.specs[1]
    heater_step =  readin.specs[2]

    n_bias = readin.specs[3]
    bias_start = readin.specs[4]
    bias_step =  readin.specs[5]

tes_heater=reform(fltarr(n_heater))
for m=0, n_heater-1 do begin
	tes_heater(m) = heater_start + m* heater_step 
endfor

tes_bias=reform(fltarr(n_bias))
for m=0, n_bias-1 do begin
	tes_bias(m) = bias_start - m* bias_step 
endfor
;stop
;__________________________________________________________________

if keyword_set(tes_heater) then plot_file = folder + date + 'analysis/' +file_name + '_multiheater_sq1x41.ps'

set_plot, 'ps'
device, filename= plot_file, /landscape


    ;ibias = i_factor * readin.bias 
a=0;15
b=n_elements(tes_bias)-1

for j=0,n_heater-1 do begin
	for k=0,40 do begin  ;  A new loop to put one address value per page.
	    for i=0, 7 do begin
	        label = 'SA Channel ' + string(i, format='(f3.0)')	
	        plot, tes_bias[a:b]/1000., readin.data[j,a:b,i,k]/1000., xtitle="tes_bias"+i_units, ytitle="Voltage"+v_units,$
	        charsize=1.2, xstyle=1, /ynozero,$
	        xrange=[min(tes_bias)/1000., max(tes_bias)/1000.], title= label
	    endfor  ; end of plotting loop in 8 columns.
	    label_bias = 'tes heater = ' + string(tes_heater(j))
	    label_row='row #'+string(k) 
	    xyouts, .1, 1.0, name_label , charsize=1.2, /normal
	    xyouts, 0.7, 1.0, label_bias , charsize=1.2, /normal
	    xyouts, 0.5, 1.0, label_row , charsize=1.2, /normal
	endfor  ; End of loop in 41 rows.
endfor
 



endelse   

print, 'HERE I AM!!'
close, 1
device, /close                  ;close ps


close, 3

spawn, 'ggv -seascape -media letter '+plot_file+' &'
fine:
;stop
end
