pro iv_analysis, filename=filename, DACbias=DACbias, plotgen=plotgen, filtered=filtered, ascii=ascii, $
                 datagen=datagen, biasfile=biasfile, setpntgen=setpntgen, $
                 array_file=array_file, array_name=array_name,post_plot=post_plot

;	Analyzes I-V curve data and generates a summary plot, with the options of additional plots and data files.
;		Input files are an MCE ramp_tes_bias data file with 33 rows
;			with a corresponding (filename).bias.old file for reading in the I-V parameters
;		A shunt resistance measurement file from the SRDP is also read in for calibration.
;		If no shunt resistance measurement is found, then a 0.7mOhm shunt is assummed.

;	If filename keyword is not set, the code will analyzed the data file in /data/cryo/last_iv_completed_name
;
;	If DACbias keyword is set to an array of bias points, then .DACpnt files will be generated with
;		TES parameters at those bias points.

;	If plotgen keyword is set, then I-V data will be plotted for each column 
;		in both the I-V and R-P planes.
;		The calibrated superconducting branch will be plotted as well to look for R_parasitic.
;		Summary plots of R_normal, P_sat at 50% of R_normal, and the applied detector bias at
;			20%, 50%, and 80% of R_normal are also plotted on the final page.

;	If filtered keyword is set then it treats the data like it's in the filtered MCE data mode = 8.
;	Otherwise, data is treated like it's in the fb + er MCE data mode = 4.

;	Ascii keyword should be set if data was acuired in text or ascii format, otherwise, it assumes the data 
;		is in binary format

;	Datagen keyword should be set to generate calibrated I-V curve output files for each detector determined
;		to have a good I-V curve.

;	Biasfile keyword will generate a file that contains the recommended biases to drive each group of columns
;		near 50% of Rn.  The default file is /data/cryo/tes_bias_recommended, and a copy of that file will
; 		be made in (filename)/tes_bias_recommended

;	Setpntgen keyword will generate .setpnt files for each working detector with detector parameters at 
;		0.2, 0.3, ..., 0.9 * Rn.

;	MDN 8-28-2007
;
;       array_name or array_file can be used to force loading of array
;       parameters for a particular array, or using a particular array config file.
;

FBbits = 14 ; 26 for FB only data mode, currently 14 for fb + er mode and for filtered mode
n_columns = 32                  ; Number of columns being analyzed
filtergain = 1216.;/2;

; if neither array_file nor array_name are defined, determine the
; array based on the contents of /data/cryo/array_id

if not keyword_set(array_file) then begin
    if not keyword_set(array_name) then begin
        openr, arf, /get_lun, '/data/cryo/array_id'
        array_name = ''
        readf, arf, array_name
        free_lun,arf
    endif
    array_file=strcompress( getenv('MAS_TEMPLATE')+'/array_'+array_name+'.cfg', /remove_all)
endif

if 1 then begin
    load_array_params,array_file, array_params

    array_name = array_params.array_name;
    Rfb = array_params.Rfb[0]
    M_ratio = array_params.M_ratio[0]
    fb_normalize = array_params.fb_normalize
    per_Rn_bias = array_params.per_Rn_bias
    per_Rn_cut = array_params.per_Rn_cut
    psat_cut = array_params.psat_cut
    ncut_lim = array_params.ncut_lim[0]

    good_shunt_range = array_params.good_shunt_range
    default_Rshunt = array_params.default_Rshunt[0]
    use_jshuntfile = array_params.use_srdp_Rshunt[0]

    Rbias_arr = array_params.Rbias_arr
    Rbias_cable = array_params.Rbias_cable
    bias1_cols = where(array_params.bias_lines mod 3 eq 0)
    bias2_cols = where(array_params.bias_lines mod 3 eq 1)
    bias3_cols = where(array_params.bias_lines mod 3 eq 2)
    eff_bias_lines = array_params.bias_lines
    bias_step = array_params.bias_step[0]

    ymins = array_params.plot_ymin
    ymaxs = array_params.plot_ymax

    jshuntfile_prefix=getenv('MAS_SCRIPT')+'/srdp_data/'+array_name+'/johnson_res.dat.C'

endif else begin
                                ; Defaults here taken from AR1 values.

    array_name = 'AR1'

    Rfb = 7006. ; S1FB resistances measured in MBAC using MCE continuity checker
    M_ratio = 8.5		; For Mux06a chips
    fb_normalize = fltarr(32) - 1.0 ; This depends on whether you have a nyquist inductor as well as the polarity of the detector bias.
                                ;per_Rn_bias = 0.4	; This is the percentage of Rnormal that the code will try to bias at; Must currently be rounded to nearest 0.1
                                ;  Changed to 0.3 11-6-2007
    per_Rn_bias = 0.3 ; This is the percentage of Rnormal that the code will try to bias at; Must currently be rounded to nearest 0.1
    
    per_Rn_cut = [.1,.8] ; These are the max and min values used to make detector cut recommendations, which will be expressed as 
    psat_cut = [1.,20.] ;	0: in range = good detector 1: out of range = bad detector in the data .run files
    ncut_lim = 500

    good_shunt_range = [ 0.0002, 0.0015 ]
    default_Rshunt = 0.0007
    use_jshuntfile = 1

                                ; Different columns use different TES bias circuitry, and this resistance takes these differences into account.
                                ; The sum of the 2 resistance values below for each column is stored in the file 'last_iv_det_data',
                                ;	 which is appended to subsequent .run files.
                                ; The first is the sum of the 6 resistors on the bias card in the TES bias circuit
                                ; Rbias_arr(0) is the bias resistance for bias card 1 (bc1), Rbias_arr(1) for bc2, and Rbias_arr(2) for bc3
    Rbias_arr = [467.,467.,467.]
                                ; Since the wiring is different, we also take into account the measured cold resistances by the continuity checker.
    Rbias_cable = [211.,210.,153.]
    bias1_cols = indgen(8)+16 ; List of columns connected to the original bias line from bias card 1
    bias2_cols = indgen(17) ; List of columns connected to the original detector heater line from bias card 2 (set to -1 if nothing is connected)
    bias2_cols(16) = 31
    bias3_cols = indgen(7)+24 ; List of columns connected to the new detector bias line from bias card 3 (set to -1 if nothing is connected)
    bias_step = 50 ;100		; This is the allowed step size that the applied biases will be rounded to, changed to 50 11-11-2007 MDN

    ymins=[.015,0,0]
    ymaxs=[.045,15,8000]
 
    ; Path on MCE_computer at Penn
    ;jshuntfile_prefix='/home/mce/actmcescripts/srdp_data/AR1/johnson_res.dat.C'
    jshuntfile_prefix='/usr/mce/mce_script/script/srdp_data/AR1/johnson_res.dat.C'
    ; Path on Feynman
    ;jshuntfile_prefix='/mnt/act2/srdp/AR1/johnson_res.dat.C'

endelse

  
Rbias_arr = Rbias_arr + Rbias_cable
biases = lonarr(3)	; These are the biases that will be applied to the 3 different bias lines

;goodpath='/data/cryo/current_data/'
if not keyword_set(filename) then begin
;  filename = dialog_pickfile(get_path=path, $
;	title='Please select an MCE I-V file.  Default data mode is Feedback + Error data.', $
;	/must_exist, path=goodpath) else filename=filename
	print, 'No I-V file keyword set => will analyze the last IV file completed in /data/cryo/last_iv_completed_name'
	openr,1,'/data/cryo/last_iv_completed_name'
	filename=' '
	readf,1,filename
	close,1
endif
print, 'Data file path: '+filename
outdir = filename+'_data'
file_mkdir, outdir

if keyword_set(post_plot) then begin
   f = strsplit(outdir,'/',/extract)
   auto_post_plot,poster,/open,dir=outdir,prefix=f[n_elements(f)-1]
endif

!path = '/home/mce/idl_pro/histogauss:'+!path

if keyword_set(filtered) then filtgain = filtergain else filtgain = 1.
if keyword_set(ascii) then binary=0 else binary=1

;S1FB card has 1V range and 50 Ohms on board (LB#6 p.5)
Rfb = Rfb+50

if !version.os_family eq 'Windows' then dirsl='\' else dirsl='/'

; Modified code to read in .bias files directly instead of using .bias.old files to calculate biases.  MDN 8-28-2007
if not file_test(filename+'.bias') then begin
	print, 'Problem finding *.bias file.  Are you sure this is an IV file?'
	print, filename
	print, 'IV analysis stopped!'
	stop
endif
raw_bias = read_ascii(filename+'.bias',data_start=1)
raw_bias = raw_bias.field1
numpts = n_elements(raw_bias)

;;Load Sweeper data from mce file. Removed IVfile keyword now that bias data is read in separately
;if keyword_set(filtered) then data = load_mce_stream_funct(filename, binary=binary, npts=numpts, bitpart=8) $ 
;	else data = load_mce_stream_funct(filename, bitpart=14,binary=binary, npts=numpts) ;,/no_status_header)
data = mas_data(filename,frame_info=frame_info)
numpts = frame_info.n_frames
n_columns = n_elements(data(*,0,0))
rf = mas_runfile(filename+'.run')
data_mode = mas_runparam(rf,'HEADER','RB rc1 data_mode',/long)

good_ivs=lonarr(n_columns)

rnorm_all=fltarr(n_columns,33)
psat_all=fltarr(n_columns,33)
vtes_all=fltarr(n_columns,33)
resp_all=fltarr(n_columns,33)
perRn_all=fltarr(n_columns,33)
setpnt_all=fltarr(n_columns,33,3)
iv_data_all=fltarr(n_columns,33,2,numpts)

for MuxColumn=0,n_columns-1 do begin

;b1c = where(bias1_cols eq muxcolumn)
;b2c = where(bias2_cols eq muxcolumn)
;b3c = where(bias3_cols eq muxcolumn)
;if b1c(0) ne -1 then rbias = Rbias_arr(0) $
;       else if b2c(0) ne -1 then rbias = Rbias_arr(1) $
;       else if b3c(0) ne -1 then rbias = Rbias_arr(2) $
;       else print, 'Problem finding column',muxcolumn, ' in bias*_cols in IV analysis code.  Check definitions.'

rbias = Rbias_arr(eff_bias_lines(muxcolumn))

if MuxColumn lt 10 then Mcol = '0'+string(MuxColumn, format='(i1)') $
	else Mcol = string(MuxColumn, format='(i2)')

Rshunt_arr=fltarr(33)
if use_jshuntfile then begin
    jshuntfile = jshuntfile_prefix+Mcol
    j_res = read_ascii(jshuntfile, comment_symbol='#')
    Rshunt_arr(j_res.field1(0,*)) = j_res.field1(1,*)
endif else begin
    jshuntfile = 'Using default of ' + string(default_Rshunt)
endelse

;print, 'Shunt Path: '+jshuntfile
good_sh_rows = where(Rshunt_arr gt good_shunt_range[0] and Rshunt_arr lt good_shunt_range[1])
;print, 'Rows with shunts between 0.2-1.0 mOhms from SRDP: ', good_sh_rows

no_srdp_shunt=where(Rshunt_arr eq 0)
Rshunt_arr(no_srdp_shunt) = default_Rshunt

if keyword_set(R_oper) then R_oper = R_oper $
		else R_oper = 0.5

Rpara_arr = fltarr(33)
Rpara_arr(*) = 0.

plotstart=0
Rnormals = fltarr(33)
Psat = fltarr(33)
setpnts = fltarr(3,33)

for j=0,32 do begin

	Row = j

	Rshunt = Rshunt_arr(Row)
	Rpara = Rpara_arr(Row)
	bad_srdp_shunt = where(good_sh_rows eq row)

	raw_array = replicate(0.,2, numpts)
	iv_array = replicate(0.,3,numpts)
	iv_array(2,*) = raw_bias 	;data.time

;	raw_array(1,*) = data.fb(MuxColumn,Row)*fb_normalize[MuxColumn]
	raw_array(1,*) = data[MuxColumn,Row,*]*fb_normalize[MuxColumn]
	raw_array_sh = shift(raw_array,0,-1)
	raw_array_der = (raw_array_sh - raw_array)	;*fb_normalize[MuxColumn]

;	stop
	; Look for giant bit jumps in the data of 2^bitmax then 2^(bitmax-1) bits and remove them
        case data_mode[0] of
           1: bitmax = 18
           9: bitmax = 24
           10: bitmax = 28
           else: print,'Unrecognized data mode:',data_mode
        endcase
;; 	if keyword_set(filtered) then begin
;;            if data_bitmax = 24 else bitmax = 18

;!MFH
        if 0 eq 1 then begin
           bitmax = bitmax - 1
           raw_array[1,*] = (raw_array[1,*] mod 2d^bitmax + 2d^bitmax) mod 2d^bitmax
           raw_array[1,*] = remove_jumps(raw_array[1,*], 2d^bitmax)
        endif else begin
	for m=0,1 do begin
		up = where(raw_array_der(1,0:numpts-2) gt 2.^(bitmax-1-m)*1.5 and raw_array_der(1,0:numpts-2) lt 2.^(bitmax-m)*1.5)
		down = where(raw_array_der(1,0:numpts-2) lt 2.^(bitmax-1-m)*(-1.5) and raw_array_der(1,0:numpts-2) gt 2.^(bitmax-m)*(-1.5))
		if up(0) ne -1 then $
			for p=0,n_elements(up)-1 do raw_array(1,0:up(p))=raw_array(1,0:up(p))+2.^(bitmax-m)
		if down(0) ne -1 then $
			for p=0,n_elements(down)-1 do raw_array(1,0:down(p))=raw_array(1,0:down(p))-2.^(bitmax-m)
        endfor
        endelse
;MFH!

;	bitmax = 18
;	for m=0,1 do begin
;		up = where(raw_array_der(1,0:numpts-2) gt 2.^(bitmax-1-m)*1.5*filtgain and raw_array_der(1,0:numpts-2) lt 2.^(bitmax-m)*1.5*filtgain)
;		down = where(raw_array_der(1,0:numpts-2) lt 2.^(bitmax-1-m)*(-1.5)*filtgain and raw_array_der(1,0:numpts-2) gt 2.^(bitmax-m)*(-1.5)*filtgain)
;		if up(0) ne -1 then $
;			for p=0,n_elements(up)-1 do raw_array(1,0:up(p))=raw_array(1,0:up(p))+2.^(bitmax-m)*filtgain
;		if down(0) ne -1 then $
;			for p=0,n_elements(down)-1 do raw_array(1,0:down(p))=raw_array(1,0:down(p))-2.^(bitmax-m)*filtgain
;	endfor

	;Normalize Vbias, 16-bit DAC, +/-2.5V with 1276 Ohm on board (LB#5 p.67 & LB#6 p.5)
	raw_array(0,*) = raw_bias/2.^16*5.	; data.time/2.^16*5.
	;Normalize Vfb, 14-bit DAC with possible offsets, 1V range, 50 Ohms on board (LB#6 p.5)
	raw_array(1,*) = raw_array(1,*)/2.^FBbits/filtgain	;*fb_normalize[MuxColumn]

	;Find the superconducting transitions by looking for the derivative to change sign
	i=0
	postnorm=0
	supercon_index=0
	trans_end_index=0
	while i le numpts-12 do begin
		if postnorm eq 0 and raw_array_der(1,i) le 0. then begin
;			if mean(raw_array_der(1,i+1:i+11)) le 0. then begin
			if median(raw_array_der(1,i+1:i+11)) le 0. then begin
				supercon_index = i
;				print, 'row ', row,'  transition start index ', supercon_index
				postnorm=1
				;i=numpts
			endif
		endif
		if postnorm eq 1 and raw_array_der(1,i) gt 100. then begin
;			if mean(raw_array_der(1,i+1:i+11)) gt 100. then begin
			if median(raw_array_der(1,i+1:i+11)) gt 100. then begin
				trans_end_index = i
;				print, 'row ', row,'  transition end index ', trans_end_index
				i=numpts
			endif
		endif
		i=i+1
	endwhile

	;To find offset, look at data on normal branch over a 0.3 V range
	;	that runs from 0.2 - 0.5 V before the supercon index
	trans_bias = raw_array(0,supercon_index)
	normal_index = where(raw_array(0,0:numpts*3/4) gt trans_bias + 0.2 and raw_array(0,0:numpts*3/4) lt trans_bias + 0.8)

	if normal_index(0) eq -1 or n_elements(normal_index) eq 1 or trans_end_index eq 0 then begin
		if keyword_set(plotgen) then begin
			if plotstart eq 0 then begin
;				print, 'plotting I-V data'
				set_plot, 'ps'
				device, /color
				TVLCT, [0,255,0,0,255,0,255,150], [0,0,255,0,0,255,255,0], [0,0,0,255,255,255,0,150]
				plotfile='IV_plots_C'+mcol+'.ps'
                                if keyword_set(post_plot) then auto_post_plot,poster,filename=plotfile
				device, FILENAME = outdir+dirsl+plotfile
				device, YOFFSET = 2, YSIZE = 24
				plotstart=1
				!p.multi=0
				plot, [0,1],[0,1], psym=3
				xyouts, .1, .67, 'MCE Data File'
				xyouts, .02, .62, outdir, charsize=0.6
				xyouts, .1, .47, 'Shunt resistance data file'
				;xyouts, .02,.42, jshuntfile, charsize=0.6
			endif
			if plotstart eq 1 then !p.multi=[0,3,6]
			plotstart=plotstart+1
			if plotstart eq 7 then plotstart=1
			plot, [0,1],[0,1], psym=3, title='RS'+strtrim(string(row),2)
			xyouts,	.1, .8, 'Could not find normal slope', charsize=.7
			xyouts,	.1, .6, '  in data at right ->', charsize=.7
			if bad_srdp_shunt(0) eq -1 then xyouts, .1, .2, 'Bad SRDP shunt measurement', charsize=.7
			plot, raw_array(0,*), raw_array(1,*), xtitle='raw tes bias data (V)', ytitle='raw fb data (V)', $
					title='RS'+strtrim(string(row),2)+' Raw Data', psym=3, /xstyle, /ystyle
			plot, [0,1],[0,1], psym=3
		endif
;		if bad_srdp_shunt(0) eq -1 then shout='. Bad SRDP shunt.' else shout='. Good SRDP shunt.'
;		print, 'Rnormal fit problem for C '+mcol+' RS '+strtrim(string(row),2)+shout

	endif else begin
		good_ivs(muxcolumn)=good_ivs(muxcolumn)+1
		norm_fit = linfit(raw_array(0,normal_index), raw_array(1,normal_index))
		;Use comparison of normalization slope with fit slope to calculate the offset for each channel
		;	See Niemack lab book #4 p.41 for details
		;offset = norm_fit(0)+(norm_fit(1)-slopes(RS))*(trans_bias + 0.015)
		;Using the line below, we no longer force the normal resistance to remain constant from curve to curve
		offset = norm_fit(0)

		;Conversion from Vbias and Vfb in volts to Vtes and Ites in uV and uA from iv_convert program
		;	FB conversion has a 20mA DAC with 50 Ohm shunt, which decreases max FB volts to < 1V
		iv_array(1,*) = (raw_array(1,*) - offset)/((-1.) * M_ratio * Rfb)*(0.02*(1/Rfb+1/50.)^(-1))
		iv_array(0,*) = Rshunt * (raw_array(0,*)/(1. * Rbias) - iv_array(1,*)) - Rpara * iv_array(1,*)
		iv_array(0:1,*) = iv_array(0:1,*) * 1000000.  ; convert from V, A to uV, uA

		iv_data_all(muxcolumn, row, 0, *) = iv_array(0,*)
		iv_data_all(muxcolumn, row, 1, *) = iv_array(1,*)

		Rnormal = mean(iv_array(0,normal_index)/iv_array(1,normal_index))

		super_fit = linfit(raw_array(0,trans_end_index:numpts-1), raw_array(1,trans_end_index:numpts-1))
		sup_array = fltarr(2, numpts-trans_end_index)

		;Convert Superconducting Branch to detector current vs. TES current based on its own normalization
		sup_array(1,*) = (raw_array(1,trans_end_index:numpts-1) - super_fit(0))/((-1.) * Rfb * M_ratio)*(0.02*(1/Rfb+1/50.)^(-1))
		sup_array(0,*) = raw_array(0,trans_end_index:numpts-1)/(1. * Rbias)

		vbias = iv_array(2,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt R_oper)))
;		print, 'Required bias in MCE DAC to set R_op to ' + strtrim(string(R_oper, format='(f5.3)'),1) + '*R_normal', vbias

		vtesbias = iv_array(0,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt R_oper)))
;		print, 'Voltage across TES at bias point in uV', vtesbias

		if row lt 10 then outfilename = 'c'+mcol+'_rs0'+string(row, format='(i1)') $
			else outfilename = 'c'+mcol+'_rs'+string(row, format='(i2)')
		if keyword_set(setpntgen) then begin
			openw, 1, outdir+dirsl+outfilename+'.setpnts'
			printf, 1,'# '+outdir+dirsl+outfilename+'.setpnts'
			printf, 1,'# set_point Vtes(uV) Ites(uV) Rtes(Ohms) Ptes(pW) Vbias_applied(DAC) Responsivity(W/DACfb) Responsivity(W/DACfiltered) R_shunt_SRDP(Ohms)'
;			print,'# set_point    Vtes(uV)     Ites(uV)     Ptes(pW)    Vbias_applied(V)'
		endif

		if trans_end_index ne 0 then begin
		for i= 0,7 do begin
			setpt = i*.1 +.2
			vtes = iv_array(0,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt setpt)))
			ites = iv_array(1,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt setpt)))
			vbias = iv_array(2,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt setpt)))
			rtes = vtes/ites
			ptes = vtes*ites
			; Responsivity in DAC units is just vtes * (1 - Rsh/Rtes) * (d Ites / d DAC)
			resp = - vtes * 1.e-6 * (1 - rshunt_arr(row)*ites/vtes) * 0.02 / ((-1.) * M_ratio * Rfb * (1/Rfb+1/50.) * 2.^FBbits)
			badsh = where(no_srdp_shunt eq row)
			if badsh(0) eq -1 then rsh=rshunt else rsh=0.
			if keyword_set(setpntgen) then printf, 1, string(setpt)+string(vtes)+string(ites)+string(rtes)+string(ptes)+string(vbias)+string(resp)+string(resp/filtergain)+string(rsh)
			if setpt eq 0.2 then setpnts(0,j) = vbias
			if setpt eq per_Rn_bias then setpnts(1,j) = vbias
			if setpt eq 0.8 then setpnts(2,j) = vbias
;			print, setpt, vtes, ites, ptes, vbias
		endfor
		endif
		if keyword_set(setpntgen) then close,1

		if keyword_set(datagen) then begin
			openw, 3, outdir+dirsl+outfilename+'_iv.dat'
			printf, 3, '# '+outdir+dirsl+outfilename+'_iv.dat'
			printf, 3, '# Vtes(uV) Ites(uA) Vbias_applied(DAC)'
			for i=0,numpts-1 do begin
				printf, 3, iv_array(0,i),iv_array(1,i),iv_array(2,i)
			endfor
			close,3
		endif

		if keyword_set(plotgen) then begin
			if plotstart eq 0 then begin
;				print, 'plotting I-V data'
				set_plot, 'ps'
				device, /color
				TVLCT, [0,255,0,0,255,0,255], [0,0,255,0,0,255,255], [0,0,0,255,255,255,0]
				plotfile='IV_plots_C'+mcol+'.ps'
                                if keyword_set(post_plot) then auto_post_plot,poster,filename=plotfile
				device, FILENAME = outdir+dirsl+plotfile
				device, YOFFSET = 2, YSIZE = 24
				plotstart=1
				!p.multi=0
				plot, [0,1],[0,1], psym=3
				xyouts, .1, .67, 'MCE Data File'
				xyouts, .02, .62, outdir, charsize=0.6
				xyouts, .1, .47, 'Shunt resistance data file'
				xyouts, .02,.42, jshuntfile, charsize=0.6
			endif
			if plotstart eq 1 then !p.multi=[0,3,6]
			plotstart=plotstart+1
			if plotstart eq 7 then plotstart=1
			plot, iv_array(0,0:trans_end_index), iv_array(1,0:trans_end_index), xtitle='TES V (uV)', $
					ytitle='TES I (uA)', title='RS'+strtrim(string(row),2)+' I-V', psym=3, /xstyle, /ystyle, xticklen=1, yticklen=1
			plot, iv_array(0,0:trans_end_index)*iv_array(1,0:trans_end_index), iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index), $
					xtitle='TES P (pW)', ytitle='TES R (Ohms)', title='RS'+strtrim(string(row),2)+' R-P', $
					psym=3, xr=[0,max(iv_array(0,0:trans_end_index)*iv_array(1,0:trans_end_index))], $
					yr=[0,max(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index))], xticklen=1, yticklen=1
			plot, sup_array(0,*), sup_array(1,*), xtitle='Det bias (A)', ytitle='TES I (A)', xr=[0,1.e-4], $
					yr=[0,1.e-4],title='RS'+strtrim(string(row),2)+' Supercon', psym=3
			if bad_srdp_shunt(0) eq -1 then xyouts, 1.e-5, 2e-5, 'Bad SRDP shunt measurement', charsize=.7
		endif
		vtes = iv_array(0,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt 0.5)))
		ites = iv_array(1,max(where(iv_array(0,0:trans_end_index)/iv_array(1,0:trans_end_index)/Rnormal gt 0.5)))
		Rnormals(j) = Rnormal
		Psat(j) = vtes*ites
	endelse
endfor
if keyword_set(plotgen) then begin
    if max(rnormals) gt 0 then begin
	!p.multi = [0,1,3]
	plot, indgen(33), Rnormals, xtitle='Row Select', ytitle='Normal Resistances (Ohms)', psym=2, charsize=1.5, yticklen=1, title=outdir, yr=[min(Rnormals(where(Rnormals gt 0))),max(Rnormals)]
	plot, indgen(33), Psat, xtitle='Row Select', ytitle='Power at 50% R_normal (pW)', psym=2, charsize=1.5, yticklen=1
	plot, indgen(33), setpnts(2,*), xtitle='Row Select', ytitle='Applied Detector Bias (DAC)', psym=2, charsize=1.5, yticklen=1
	oplot, indgen(33), setpnts(1,*), psym = 4
	oplot, indgen(33), setpnts(0,*), psym = 5
	xyouts, 34,setpnts(2,31),'80% Rn'
	xyouts, 34,setpnts(1,31),string(per_Rn_bias*100,format='(i2)')+'% Rn'
	xyouts, 34,setpnts(0,31),'20% Rn'
;	print, Rnormals, Psat
    endif
    device, /close
endif

rnorm_all(muxcolumn,*)=Rnormals
psat_all(muxcolumn,*)=psat
setpnt_all(muxcolumn,*,2)=setpnts(2,*)
setpnt_all(muxcolumn,*,1)=setpnts(1,*)
setpnt_all(muxcolumn,*,0)=setpnts(0,*)

if muxcolumn eq 0 then print, 'Good normal branches found in each column:'
print, 'Column '+mcol+' = '+strtrim(good_ivs(muxcolumn))
;stop
endfor
print, 'Total good normal branches = '+strtrim(total(good_ivs),1)

set_plot, 'ps'
device, /color
TVLCT, [0,255,0,0,255,0,255,150], [0,0,255,0,0,255,150,100], [0,0,0,255,255,255,0,100]
plotfile='IV_summary.ps'
if keyword_set(post_plot) then auto_post_plot,poster,filename=plotfile
device, FILENAME = outdir+dirsl+plotfile
device, YOFFSET = 2, YSIZE = 24
!p.multi=[0,1,3]
print, 'Generating summary plot: '+outdir+dirsl+plotfile

syms = [1,2,4,7]
symchars = ['+','*','o','x']
symsz = 0.5
for i=0,n_columns-1 do begin
	if i eq 0 then begin
		plot, indgen(33), Rnorm_all(i,*), xtitle='Row Select', ytitle='Normal Resistances (Ohms)', psym=2, charsize=1.5, yticklen=1, title=outdir, yr=[ymins(0),ymaxs(0)], symsize=symsz
	endif else begin
		oplot, indgen(33), Rnorm_all(i,*), psym=syms(i/8),color=i mod 8, symsize=symsz
	endelse
	;xyouts, 34, ymaxs(0) - (.62-.08*i)*(ymaxs(0)-ymins(0)),'C '+strtrim(i,1), color=i mod 8
endfor

for i=0,n_columns-1 do begin
	if i eq 0 then begin
		plot, indgen(33), Psat_all(i,*), xtitle='Row Select', ytitle='Power at 50% R_normal (pW)', psym=2, charsize=1.5, yticklen=1,yr=[ymins(1),ymaxs(1)], symsize=symsz
	endif else begin
		oplot, indgen(33), Psat_all(i,*), psym=syms(i/8), color=i mod 8, symsize=symsz
	endelse
	;xyouts, 34, ymaxs(1) - (.62-.08*i)*(ymaxs(1)-ymins(1)),'C '+strtrim(i,1), color=i
endfor

for i=0,n_columns-1 do begin
	if i eq 0 then begin
		plot, indgen(33), setpnt_all(i,*,2), xtitle='Row Select', ytitle='Applied Detector Bias (DAC)', psym=2, charsize=1.5, yticklen=1,yr=[ymins(2),ymaxs(2)], symsize=symsz
;		oplot, indgen(33), setpnt_all(i,*,1), psym = 4
		oplot, indgen(33), setpnt_all(i,*,0), psym = 5, symsize=symsz
		oplot, [35], [ymaxs(2) - .7*(ymaxs(2)-ymins(2))],psym=2, symsize=symsz
		xyouts, [36], [ymaxs(2) - .72*(ymaxs(2)-ymins(2))],'80% Rn'
;		oplot, [35], [ymaxs(2) - .82*(ymaxs(2)-ymins(2))],psym=4
;		xyouts, [36], [ymaxs(2) - .82*(ymaxs(2)-ymins(2))],'50% Rn'
		oplot, [35], [ymaxs(2) - .8*(ymaxs(2)-ymins(2))],psym=5, symsize=symsz
		xyouts, [36], [ymaxs(2) - .82*(ymaxs(2)-ymins(2))],'20% Rn'
	endif else begin
		oplot, indgen(33), setpnt_all(i,*,2), psym=2, color=i mod 8, symsize=symsz
;		oplot, indgen(33), setpnt_all(i,*,1), psym = 4, color=i
		oplot, indgen(33), setpnt_all(i,*,0), psym = 5, color=i mod 8, symsize=symsz
	endelse

	xyouts, 32, ymaxs(2) - (.62-.08*i)*(ymaxs(2)-ymins(2)),symchars(i/8)+'  C '+strtrim(i,1)+' gd '+strtrim(good_ivs(i),1), color=i mod 8
endfor

xyouts, 30, ymaxs(2) - (.62-.08*38)*(ymaxs(2)-ymins(2)),'Total good = '+string(total(good_ivs),format='(i3)')

;Very rough calculation of a good bias to bias the detectors near the middle of the transition.
;bias_cnt=0.
;bias_tot=0.
;for i=0,7 do begin
;	good_det = where(setpnt_all(i,*,0) gt 1000 and setpnt_all(i,*,0) lt 20000 and setpnt_all(i,*,2) gt 1000 and setpnt_all(i,*,2) lt 20000)
;	if good_det(0) ne -1 then begin
;		bias_tot = total(setpnt_all(i,good_det,0))+total(setpnt_all(i,good_det,2))+bias_tot
;		bias_cnt = bias_cnt+n_elements(good_det)*2
;	endif
;endfor
;C07bias = bias_tot/bias_cnt

print, 'Recommended biases to reach '+string(per_Rn_bias*100,format='(i2)')+'% Rn:'
;if n_elements(C07bias) eq 1 then print, 'Columns 0-7:   '+string(C07bias,format='(i5)') else print, 'Did not find a good bias value for Columns 0-7.'

if bias1_cols(0) ge 0 then begin
  nrow=n_elements(setpnt_all(0,*,1))
  bias1pnts = fltarr(n_elements(bias1_cols)*nrow)
  for i=0,n_elements(bias1_cols)-1 do bias1pnts(i*nrow:(i+1)*nrow-1) = setpnt_all(bias1_cols(i),*,1)
  good_det = where(bias1pnts gt 100. and bias1pnts lt 10000)
  if good_det(0) ne -1 then begin

;COMMENTED OUT LINES TO USE HISTOGAUSS FOR DOING A GAUSSIAN FIT TO THE BIAS VALUE DISTRIBUTION, BECAUSE THEY WEREN'T FITTING WELL.
;	GO BACK TO JUST USING THE MEDIAN FOR NOW.
;	tit = string(per_Rn_bias*100,format='(i2)')+'% Rn biasing histogram for columns '+strtrim(bias1_cols(0),1)+'-'+strtrim(bias1_cols(n_elements(bias1_cols)-1),1)
;	if good_det(0) ne -1 then histogauss, bias1pnts(good_det), bias1fit, xx, charsize=1, _extra='yr=[4000,12000]'
;	xyouts,xx(0), bias1fit(0)*.8, tit, color=1, charsize=1.3
;	biases(0) = round(bias1fit(1)/bias_step)*bias_step
;	xyouts,xx(0), bias1fit(0)*.6, 'Planned bias = '+strtrim(biases(0),1), color=1, charsize=1.3
	biases(0) = round(median(bias1pnts(good_det))/bias_step)*bias_step
  endif
  print, 'Columns '+strtrim(bias1_cols(0),1)+'-'+strtrim(bias1_cols(n_elements(bias1_cols)-1),1)+' = ',biases(0)
endif

if bias2_cols(0) ge 0 then begin
  bias2pnts = fltarr(n_elements(bias2_cols)*nrow)
  for i=0,n_elements(bias2_cols)-1 do bias2pnts(i*nrow:(i+1)*nrow-1) = setpnt_all(bias2_cols(i),*,1)
  good_det = where(bias2pnts gt 100. and bias2pnts lt 20000)
  if good_det(0) ne -1 then begin
;	tit = string(per_Rn_bias*100,format='(i2)')+'% Rn biasing histogram for columns '+strtrim(bias2_cols(0),1)+'-'+strtrim(bias2_cols(n_elements(bias2_cols)-1),1)
;	if good_det(0) ne -1 then histogauss, bias2pnts(good_det), bias2fit, xx, charsize=1
;	xyouts,xx(0), bias2fit(0)*.8, tit, color=1, charsize=1.3
;	biases(1) = round(bias2fit(1)/bias_step)*bias_step
;	xyouts,xx(0), bias2fit(0)*.6, 'Planned bias = '+strtrim(biases(1),1), color=1, charsize=1.3
	biases(1) = round(median(bias2pnts(good_det))/bias_step)*bias_step
  endif
  print, 'Columns '+strtrim(bias2_cols(0),1)+'-'+strtrim(bias2_cols(n_elements(bias2_cols)-1),1)+' = ',biases(1)
endif

;stop

if bias3_cols(0) ge 0 then begin
  bias3pnts = fltarr(n_elements(bias3_cols)*nrow)
  for i=0,n_elements(bias3_cols)-1 do bias3pnts(i*nrow:(i+1)*nrow-1) = setpnt_all(bias3_cols(i),*,1)
  good_det = where(bias3pnts gt 100. and bias3pnts lt 20000)
  if good_det(0) ne -1 then begin
;	tit = string(per_Rn_bias*100,format='(i2)')+'% Rn biasing histogram for columns '+strtrim(bias3_cols(0),1)+'-'+strtrim(bias3_cols(n_elements(bias3_cols)-1),1)
;	if good_det(0) ne -1 then histogauss, bias3pnts(good_det), bias3fit, xx, charsize=1
;	xyouts,xx(0), bias3fit(0)*.8, tit, color=1, charsize=1.3
;	biases(2) = round(bias3fit(1)/bias_step)*bias_step
;	xyouts,xx(0), bias3fit(0)*.6, 'Planned bias = '+strtrim(biases(2),1), color=1, charsize=1.3
	biases(2) = round(median(bias3pnts(good_det))/bias_step)*bias_step
  endif
  print, 'Columns '+strtrim(bias3_cols(0),1)+'-'+strtrim(bias3_cols(n_elements(bias3_cols)-1),1)+' = ',biases(2)
endif

Rn_per_all = fltarr(n_columns, 33)
cut_rec_all = fltarr(n_columns, 33)

if keyword_set(DACbias) then nbiases = n_elements(dacbias)+1 else nbiases=1
for MuxColumn=0,n_columns-1 do begin
	if MuxColumn lt 10 then Mcol = '0'+string(MuxColumn, format='(i1)') $
		else Mcol = string(MuxColumn, format='(i2)')
	b1check = where(bias1_cols eq muxcolumn)
	b2check = where(bias2_cols eq muxcolumn)
	b3check = where(bias3_cols eq muxcolumn)
	if b1check(0) ne -1 then rbias = biases(0) $	
		else if b2check(0) ne -1 then rbias = biases(1) $
		else if b3check(0) ne -1 then rbias = biases(2) $
		else print, 'Problem finding column',muxcolumn, ' in bias*_cols in IV analysis code.  Check definitions.'
	for row=0,32 do begin
		if row lt 10 then outfilename = 'c'+mcol+'_rs0'+string(row, format='(i1)') $
			else outfilename = 'c'+mcol+'_rs'+string(row, format='(i2)')

		if Psat_all(muxcolumn,row) ne 0. then begin
			if keyword_set(DACbias) then begin
				openw, 2, outdir+dirsl+outfilename+'.DACpnt'
				printf,2,'# '+outdir+dirsl+outfilename+'.DACpnt'
				printf,2,'# Rtes/Rn Vtes(uV) Ites(uV) Rtes(Ohms) Ptes(pW) Vbias_applied(DAC) Responsivity(W/DACfb) Responsivity(W/DACfiltered) R_shunt_SRDP(Ohms)'
			endif
			for i=0,nbiases-1 do begin
				if i eq 0 then bcur = rbias else bcur = dacbias(i-1)
				pnt = min(where(raw_bias le bcur))
				vtes = iv_data_all(muxcolumn,row,0,pnt)
				ites = iv_data_all(muxcolumn,row,1,pnt)
				vbias = raw_bias(pnt)
				rtes = vtes/ites
				ptes = vtes*ites
				rtesp = vtes/ites/Rnorm_all(muxcolumn,row)
				if i eq 0 then Rn_per_all(muxcolumn, row) = rtesp
				; Responsivity in DAC units is just vtes * (1 - Rsh/Rtes) * (d Ites / d DAC)
				resp = - vtes * 1.e-6 * (1 - rshunt_arr(row)*ites/vtes) * 0.02 / ((-1.) * M_ratio * Rfb * (1/Rfb+1/50.) * 2.^FBbits)
				badsh = where(no_srdp_shunt eq row)
				if badsh(0) eq -1 then rsh=rshunt else rsh=0.
				if keyword_set(DACbias) then printf, 2, string(rtesp)+string(vtes)+string(ites)+string(rtes)+string(ptes)+string(vbias)+string(resp)+string(resp/filtergain)+string(rsh)
				;print, rtes, vtes, ites, ptes, vbias
				if i eq 0 then begin
					resp_all(muxcolumn,row) = resp
					vtes_all(muxcolumn,row) = vtes
					psat_all(muxcolumn,row) = ptes
					perRn_all(muxcolumn,row) = rtesp
					if ptes gt psat_cut(0) and ptes lt psat_cut(1) and rtesp gt per_Rn_cut(0) and rtesp lt per_Rn_cut(1) then $
						cut_rec_all(muxcolumn, row) = 0. $
						else cut_rec_all(muxcolumn, row) = 1.
				endif
			endfor
			if keyword_set(DACbias) then close,2
;	stop
		endif else begin
			cut_rec_all(muxcolumn, row) = 1.
		endelse
	endfor
endfor

not_cut = n_elements(where(cut_rec_all eq 0))
print, 'Cut limits at recommended biases:'
print, '% R_n ', per_Rn_cut 
print, 'Po (pW) ', psat_cut
print, 'Number of detectors within cut limits = '+strtrim(not_cut,1)
xyouts, 30, ymaxs(2) - (.62-.08*36.5)*(ymaxs(2)-ymins(2)), 'Within cut = '+string(not_cut,format='(i3)')

!p.multi=[0,1,3]
ymins = 0.05
ymaxs = 0.95
numbins = 10

if bias1_cols(0) ge 0 then begin
	bhist = histogram(Rn_per_all(bias1_cols,*), min = ymins(0), max= ymaxs(0), nbins=numbins(0),locations=binloc)
	plot, binloc, bhist, psym=10, charsize=1.6, ytitle='Number of detectors', thick=3, xtitle='Ro/Rn', $	
		title='Resistance ratio (goal = .'+string(per_Rn_bias*100,format='(i2)')+' ) at bias = '+strtrim(biases(0),1)+' for columns '+strtrim(bias1_cols(0),1)+'-'+strtrim(bias1_cols(n_elements(bias1_cols)-1),1)
	maxplt = max(bhist)
	for dd=0,n_elements(bias1_cols)-1 do begin
		bhist = histogram(Rn_per_all(bias1_cols(dd),*), min = ymins(0), max= ymaxs(0), nbins=numbins(0),locations=binloc)
		if dd lt 8 then begin
			xyouts,0.05, maxplt*(.9-.9/8*dd),'C'+strtrim(bias1_cols(dd),1), color=dd
			oplot, binloc,bhist, color=dd
		endif else begin
			xyouts,0.95, maxplt*(.9-.9/8*(dd-8)), 'C'+strtrim(bias1_cols(dd),1), color=dd-8
			oplot, binloc,bhist, color=dd-8, linestyle=2
		endelse	
	endfor
	if n_elements(bias1_cols) gt 8 then xyouts, 0.03, maxplt*.97, 'Solid' 
	if n_elements(bias1_cols) gt 8 then xyouts, 0.91, maxplt*.97, 'Dashed'
endif

if bias2_cols(0) ge 0 then begin
	bhist = histogram(Rn_per_all(bias2_cols,*), min = ymins(0), max= ymaxs(0), nbins=numbins(0),locations=binloc)
	plot, binloc, bhist, psym=10, charsize=1.6, ytitle='Number of detectors', thick=3, xtitle='Ro/Rn',  $	
		title='Resistance ratio at recommended bias = '+strtrim(biases(1),1)+' for columns '+strtrim(bias2_cols(0),1)+'-'+strtrim(bias2_cols(n_elements(bias2_cols)-1),1)
	maxplt = max(bhist)
	for dd=0,n_elements(bias2_cols)-1 do begin
		bhist = histogram(Rn_per_all(bias2_cols(dd),*), min = ymins(0), max= ymaxs(0), nbins=numbins(0),locations=binloc)
		if dd lt 8 then begin
			xyouts,0.05, maxplt*(.9-.9/8*dd),'C'+strtrim(bias2_cols(dd),1), color=dd
			oplot, binloc,bhist, color=dd
		endif else begin
			xyouts,0.95, maxplt*(.9-.9/8*(dd-8)), 'C'+strtrim(bias2_cols(dd),1), color=dd-8
			oplot, binloc,bhist, color=dd-8, linestyle=2
		endelse	
	endfor
	if n_elements(bias2_cols) gt 8 then xyouts, 0.03, maxplt*.97, 'Solid' 
	if n_elements(bias2_cols) gt 8 then xyouts, 0.91, maxplt*.97, 'Dashed'
endif

if bias3_cols(0) ge 0 then begin
	bhist = histogram(Rn_per_all(bias3_cols,*), min = ymins(0), max= ymaxs(0), nbins=numbins(0),locations=binloc)
	plot, binloc, bhist, psym=10, charsize=1.6, ytitle='Number of detectors', thick=3, xtitle='Ro/Rn',  $	
		title='Resistance ratio at recommended bias = '+strtrim(biases(2),1)+' for columns '+strtrim(bias3_cols(0),1)+'-'+strtrim(bias3_cols(n_elements(bias3_cols)-1),1)
	maxplt = max(bhist)
	for dd=0,n_elements(bias3_cols)-1 do begin
		bhist = histogram(Rn_per_all(bias3_cols(dd),*), min = ymins(0), max= ymaxs(0), nbins=numbins(0),locations=binloc)
		if dd lt 8 then begin
			xyouts,0.05, maxplt*(.9-.9/8*dd),'C'+strtrim(bias3_cols(dd),1), color=dd
			oplot, binloc,bhist, color=dd
		endif else begin
			xyouts,0.95, maxplt*(.9-.9/8*(dd-8)), 'C'+strtrim(bias3_cols(dd),1), color=dd-8
			oplot, binloc,bhist, color=dd-8, linestyle=2
		endelse	
	endfor
	if n_elements(bias3_cols) gt 8 then xyouts, 0.03, maxplt*.97, 'Solid' 
	if n_elements(bias3_cols) gt 8 then xyouts, 0.91, maxplt*.97, 'Dashed'
endif

; Generate a file that can be run to set the recommended TES bias values
openw,1, outdir+'/tes_bias_recommended'
printf,1,'#!/bin/csh'
printf,1, '# Recommended biases to reach '+string(per_Rn_bias*100,format='(i2)')+'% Rn'
printf,1, '#   from IV file: '+filename
printf,1,'bias_tess '+strtrim(biases(0),1)+' '+strtrim(biases(1),1)+' '+strtrim(biases(2),1)
close,1
file_chmod, outdir+'/tes_bias_recommended',/a_execute

; Generate a file that contains the detector data at the recommended biases
openw,1, outdir+'/last_iv_det_data'
printf,1,'<IV>'
printf,1, '<iv_file> '+filename
printf,1, '<target_percent_Rn> '+string(per_Rn_bias*100,format='(i2)')
printf,1, '<bias_resistances_used> '+strtrim(Rbias_arr(0),1)+' '+strtrim(Rbias_arr(1),1)+' '+strtrim(Rbias_arr(2),1)
printf,1, '<rec_biases> '+strtrim(biases(0),1)+' '+strtrim(biases(1),1)+' '+strtrim(biases(2),1)
printf,1, '<cut_per_Rn> '+strtrim(per_Rn_cut(0),1)+' '+strtrim(per_Rn_cut(1),1)
printf,1, '<cut_bias_power(pW)> '+strtrim(Psat_cut(0),1)+' '+strtrim(Psat_cut(1),1)
printf,1, '<iv_curves_found> '+strtrim(total(good_ivs),1)
printf,1, '<detectors_within_cut> '+strtrim(not_cut,1)
for c=0,n_columns-1 do begin
	tmpstr=''
	for r=0,32 do tmpstr = tmpstr + ' '+strtrim(resp_all(c,r),1)
	printf,1,'<Responsivity(W/DACfb)_C'+strtrim(c,1)+'>'+tmpstr
endfor
for c=0,n_columns-1 do begin
	tmpstr=''
	for r=0,32 do tmpstr = tmpstr + ' '+strtrim(perRn_all(c,r),1)
	printf,1,'<Percentage_Rn_C'+strtrim(c,1)+'>'+tmpstr
endfor
for c=0,n_columns-1 do begin
	tmpstr=''
	for r=0,32 do tmpstr = tmpstr + ' '+strtrim(psat_all(c,r),1)
	printf,1,'<Bias_Power(pW)_C'+strtrim(c,1)+'>'+tmpstr
endfor
for c=0,n_columns-1 do begin
	tmpstr=''
	for r=0,32 do tmpstr = tmpstr + ' '+strtrim(vtes_all(c,r),1)
	printf,1,'<Bias_Voltage(uV)_C'+strtrim(c,1)+'>'+tmpstr
endfor
for c=0,n_columns-1 do begin
	tmpstr=''
	for r=0,32 do tmpstr = tmpstr + ' '+string(cut_rec_all(c,r),format='(i1)')
	printf,1,'<cut_rec_C'+strtrim(c,1)+'>'+tmpstr
endfor
printf,1,'</IV>'
close,1
file_chmod, outdir+'/last_iv_det_data',/a_read
device,/close

if keyword_set(biasfile) then begin
	if not_cut gt ncut_lim then begin
		spawn, 'cp -fp '+outdir+'/tes_bias_recommended /data/cryo/'
                det_data_link = '/data/cryo/last_iv_det_data'
                spawn, 'rm -f ' + det_data_link
		spawn, 'ln -s '+outdir + '/last_iv_det_data ' + det_data_link
	endif
;; 	if file_search('/misc/mce_plots',/test_directory) eq '/misc/mce_plots' then begin
;; 		spawn, 'cp -rf '+outdir+' /misc/mce_plots/'
;; 		dir_name = strsplit(outdir,'/',/extract)
;; 		spawn, 'chgrp -R mceplots /misc/mce_plots/'+dir_name(n_elements(dir_name)-1)
;; 	endif
endif
	
if keyword_set(post_plot) then auto_post_plot,poster,/close

;stop

end
