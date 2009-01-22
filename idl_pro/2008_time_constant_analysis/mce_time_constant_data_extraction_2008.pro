pro mce_time_constant_data_extraction_2008, dir=dir

if keyword_set(dir) then begin
    dir = dir
endif else begin
     dir = '/data/cryo/20081213/'
endelse
plotgen=1
fftgen=1
fftplotgen=0

numreq=2.^14

filtgain=1.
M_ratio = 8.5
FBbits = 14			; 26 for FB only data mode, currently 14 for er + fb
Rfb = 7000. 		; Resistances measured in CCam at AMEC lab book, p.20 using GPIB tester
Rfb = Rfb+50.  		;S1FB card has 1V range and 50 Ohms on board (LB#6 p.5)
peak_pl_min = 50
;backminmax=[20,50]
backminmax=[100,200]

dsl='/'

files = file_search(dir+'*_chopper_offset_biasnom*')
nfiles=n_elements(files)
filetags=lonarr(nfiles,4) 	; Bias number, Frequency, c-time, and .run flag for each file
nbiases=1			; Bias number starts at 0, so this should start at 1 to be consistent with nfreqs
nfreqs=0
for i=0,n_elements(files)-1 do begin
	f1=strsplit(files(i),'chopper_offset_biasnom', /extract,/regex)
	f2=strsplit(f1(1),'_',/extract,/regex)
	biasnum=0
	newbias = where(filetags(*,0) eq biasnum)
	if newbias(0) eq -1 then nbiases=nbiases+1
	filetags(i,0)=biasnum
	;f3=strsplit(f2(1),'Hz.',/extract,/regex)
	f3=strsplit(f2(0),'Hz',/extract,/regex)
	freq=f3(0)
        newfreq = where(filetags(*,1) eq freq)
        if newfreq(0) eq -1 then nfreqs=nfreqs+1
        filetags(i,1)=freq
	;f4=strsplit(f3(1),'.run',/extract,/regex)
	f4=strsplit(f1(0),'/',/extract,/regex)
	timestamp=strsplit(f4(n_elements(f4)-1),'_',/extract,/regex)
	filetags(i,2)=timestamp
	;dot_run=stregex(f3(1),'.run',/boolean)
	dot_run=stregex(f2(0),'.run',/boolean)
	filetags(i,3)=dot_run
;	stop
endfor	

;dfiles=where(filetags(*,3) eq 0)

for column=0,31 do begin
for b=0,nbiases-1 do begin

if plotgen then begin
	set_plot, 'ps'
	device, /color
	TVLCT, [0,255,0,0,255,0,255], [0,0,255,0,0,255,255], [0,0,0,255,255,255,0]
	if fftplotgen then begin
		device, FILENAME = dir+dsl+'fft_plots_C'+strtrim(column,1)+'_b'+strtrim(b,1)+'.ps'
		!p.multi=[0,2,6]
	endif else begin
		device, FILENAME = dir+dsl+'peak_plots_C'+strtrim(column,1)+'_b'+strtrim(b,1)+'.ps'
		!p.multi=[0,3,6]
	endelse
	device, YOFFSET = 2, YSIZE = 22
	!p.charsize=1
endif

;stop
dfiles=where(filetags(*,0) eq b and filetags(*,3) eq 0)
ndfiles=n_elements(dfiles)

peak_lev_def = 0
for i=0,ndfiles-1 do begin
	fname = files(dfiles(i))
	if file_test(fname) and not file_test(fname,/directory) then begin
            print, 'Current Column: ',column
	    print, 'Current file: '+fname
	    numpnts=numreq
	    rawdata=load_mce_stream_funct_32x32(fname,npts=numpnts,bitpart=14,/binary)
	    if numreq eq n_elements(rawdata.time) then begin
		if fftgen then spawn, 'mkdir '+fname+'_ffts'
		time = rawdata.time
		rawdata = rawdata.fb(column,*)
		nrows =n_elements(rawdata(0,*,0))
		If peak_lev_def eq 0 then begin
			peak_levels = fltarr(nrows+1,ndfiles,2)
			peak_levels(0,*,0) = filetags(dfiles,2)  ;This is the file acquisition times
			peak_levels(0,*,1) = filetags(dfiles,1)  ;This is the chopper frequency
			peak_lev_def = 1
		endif
		freqs=filetags(dfiles,1)
		if plotgen then if fftplotgen then !p.multi=[0,2,6] else !p.multi=[0,3,6]
		for j=0,nrows-1 do begin
			curdata = rawdata(0,j,*)/((2.^fbbits)*Rfb*M_ratio*filtgain)*0.02*(1/50.+1/Rfb)^(-1)
			ffit = linfit(lindgen(n_elements(curdata)),curdata)
			curdata = curdata-(ffit(0)+ffit(1)*lindgen(n_elements(curdata)))
			dfcur=pspec_total(curdata,1/time(1),timebin=1)
			if plotgen then begin
				if fftplotgen then begin 
					plot, dfcur(*,0),dfcur(*,1), /xlog, xr=[.5,200], /xstyle, $
                                		xtitle='Frequency (Hz)', ytitle='rt(PSD) (A/rt(Hz))',$
                                		title=strtrim(freqs(i),1)+'Hz chopper response for RS.'+strtrim(j,1), $
						yr=[1e-10,2e-7],/ylog
				endif else begin
					plot, dfcur(*,0),dfcur(*,1), xr=[freqs(i)-10,freqs(i)+10], $	; psym=1
						xtitle='Frequency (Hz)', ytitle='rt(PSD) (A/rt(Hz))',$
						title=strtrim(freqs(i),1)+'Hz chopper response for RS.'+strtrim(j,1), /ylog
				endelse
			endif
			peak_pnt = where((dfcur(*,0) eq min(abs(dfcur(*,0) - freqs(i)))+freqs(i)) or $
					(dfcur(*,0) eq -min(abs(dfcur(*,0) - freqs(i)))+freqs(i)))
			;print, peak_pnt
			if freqs(i) lt 5 then begin
				background = mean(dfcur(peak_pnt+backminmax(0):peak_pnt+backminmax(1),1))
				if plotgen then oplot, [freqs(i),freqs(i)+10],[background,background], color=1
				if plotgen then oplot,dfcur(peak_pnt:peak_pnt+1,0),dfcur(peak_pnt:peak_pnt+1,1), psym=2, color=2
				peak_levels(j+1,i,0) = [total(dfcur(peak_pnt:peak_pnt+1,1)^2)-2*(background^2)]^0.5
				peak_levels(j+1,i,1) = background
			endif else begin
			    if freqs(i) gt 193 then begin
				background = (mean(dfcur(peak_pnt-backminmax(1):peak_pnt-backminmax(0),1)))
				if plotgen then oplot, [freqs(i)-10,freqs(i)],[background,background], color=1
				if plotgen then oplot,dfcur(peak_pnt-peak_pl_min:peak_pnt+peak_pl_min,0),dfcur(peak_pnt-peak_pl_min:peak_pnt+peak_pl_min,1), psym=2, color=2
				peak_levels(j+1,i,0) = [total(dfcur(peak_pnt-peak_pl_min:peak_pnt+peak_pl_min,1)^2)-(peak_pl_min*2+1)*(background^2)]^0.5
				peak_levels(j+1,i,1) = background
			    endif else begin
				background = (mean(dfcur(peak_pnt-backminmax(1):peak_pnt-backminmax(0),1))+ $
                                              mean(dfcur(peak_pnt+backminmax(0):peak_pnt+backminmax(1),1)))/2
				if plotgen then oplot, [freqs(i)-3.9,freqs(i)+10],[background,background], color=1, thick=4
				if plotgen then oplot,dfcur(peak_pnt-peak_pl_min:peak_pnt+peak_pl_min,0),dfcur(peak_pnt-peak_pl_min:peak_pnt+peak_pl_min,1), psym=2, color=2, symsize=0.5
				peak_levels(j+1,i,0) = [total(dfcur(peak_pnt-peak_pl_min:peak_pnt+peak_pl_min,1)^2)-(peak_pl_min*2+1)*(background^2)]^0.5
				peak_levels(j+1,i,1) = background
			    endelse
			endelse
			;print, peak_levels(j+1,i)
			if fftgen then begin
				get_lun, ff
				openw, ff, fname+'_ffts'+dsl+'C'+strtrim(column,1)+'_RS'+strtrim(j,1)+'_fft.dat'
				printf, ff, '#Freq(Hz) Noise(A/rt(Hz))'
				pts = where(dfcur(*,0) lt 405)
				for k=0,n_elements(pts)-1 do printf,ff, strtrim(dfcur(pts(k),0),1)+' '+strtrim(dfcur(pts(k),1),1)
				close, ff
				free_lun, ff
			endif
		endfor
		;stop
	    endif else begin
		print, 'Incomplete data file: '+fname
	    endelse
	endif else begin
		;print, 'File not found: '+fname
	endelse
;if i eq 3 then stop
endfor

if plotgen then device,/close

get_lun, nf
openw, nf, dir+dsl+'peak_data_C'+strtrim(column,1)+'_b'+strtrim(b,1)+'.dat'
head = 'Scan Freq '
for j=0,nrows-1 do head = head+'RS'+strtrim(j,1)+'peak '+'RS'+strtrim(j,1)+'back '

printf, nf, head
for i=0,n_elements(freqs)-1 do begin
	line = ''
	for j=0,nrows do line=line+strtrim(peak_levels(j,i,0),1)+' '+strtrim(peak_levels(j,i,1),1)+' '
	printf, nf, line
endfor
close, nf
free_lun, nf

endfor
endfor

;stop

end
