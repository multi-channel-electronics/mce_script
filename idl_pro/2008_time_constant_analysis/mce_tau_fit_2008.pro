pro mce_tau_fit_2008

path='/mnt/act2/mce_mbac/AR1/'
dir = ['20081212/']
dsl = '/'
badfreq=[0]
nbiases=1
data_mode=10

runfile=path+dir+'1229123707_chopper_biasnom_4Hz.run'
runpr = 1

filepref = 'peak_data'

ncols=32
nrows=33

filter = read_ascii('MCE_filter_response.txt', comment_symbol='#')
filter = filter.field1
;stop

rss = indgen(33)

for d=0,n_elements(dir)-1 do begin

tau_fits = fltarr(3,nrows,nbiases(d),ncols)

for c=0,ncols-1 do begin

set_plot, 'ps'
device, /color
TVLCT, [0,255,0,0,255,0,255], [0,0,255,0,0,255,255], [0,0,0,255,255,255,0]
device, FILENAME = path+dir(d)+dsl+'tau_fits'+'_c'+strtrim(c,1)+'.ps'
device, YOFFSET = 2, YSIZE = 26
!p.charsize=1

for b=0,nbiases(d)-1 do begin

file=filepref+'_C'+strtrim(c,1)+'_b'+strtrim(b,1)+'.dat'
print,'analyzing: '+dir(d)+file
noise_peaks = read_ascii(path+dir(d)+file,data_start=1)  ;Skip freq=0 row
noise_peaks = noise_peaks.field01
nrowsdat = (n_elements(noise_peaks(*,0))-2)/2

if nrowsdat ne nrows then begin
	print, 'Number of rows found in data file was '+strtrim(nrowsdat,1)+', '+strtrim(nrows)+' were expected.'
	stop
endif

if runpr then begin
	rp = read_ascii(runfile, data_start=236)
	rp = rp.field01
	p = rp(1:33,32:63)
	rp = rp(1:33,0:31)
	;stop
endif

!p.multi=[0,3,6]

minpnts_fit=5

for i=1,nrows do begin
    gooddat = where(noise_peaks(i*2,*) gt 0)
    if n_elements(gooddat) gt minpnts_fit then begin ;if gooddat(0) ne -1 then begin
		scanint = round((noise_peaks(0,*) - min(noise_peaks(0,gooddat)))/1.e4)
		resp_med = median(noise_peaks(i*2,gooddat))
		;Only use points that are an order of magnitude above or below the median response value.
		gooddat = where(noise_peaks(i*2,*) gt 0 and noise_peaks(i*2,*) le resp_med*10. and  noise_peaks(i*2,*) ge resp_med/10.)
		; For 20070302/chopper_B.25V_T.38, we need to throw out the last few files acquired (high scanint files), because the 0.3K stage ran out.
;		gooddat = where(noise_peaks(i*2,*) gt 0 and noise_peaks(i*2,*) le resp_med*10. and  noise_peaks(i*2,*) ge resp_med/10. and scanint lt max(scanint))
		if n_elements(gooddat) gt minpnts_fit then begin	
			freq = reform(noise_peaks(1,gooddat))
			bf = lonarr(n_elements(freq))
			for j=0,n_elements(freq)-1 do begin
				t = where(badfreq eq freq(j))
				if t(0) ne -1 then bf(j)=1
			endfor
			gf = where(bf eq 0)
			gooddat = gooddat(gf)
			freq = reform(noise_peaks(1,gooddat))
			filter_pnts = fltarr(n_elements(freq))
			fit_sig = reform(noise_peaks(i*2,gooddat))

			if data_mode ne 4 then begin
				for fp = 0,n_elements(freq)-1 do begin
					filter_pnts(fp) = filter(1,where(abs(freq(fp)-filter(0,*)) eq min(abs(freq(fp)-filter(0,*)))))
				endfor
				filter_pnts = filter_pnts/filter(1,0)
				fit_sig = fit_sig/filter_pnts
			endif 
	; Remove half of data points to compare results
	;		nfreq=n_elements(freq)/2
	;		freq = freq(nfreq:nfreq*2-1)
	;		fit_sig = fit_sig(nfreq:nfreq*2-1)


;		;Test putting background back in background that was previously subtracted
;			stop
;			fit_sig = reform((noise_peaks(i*2,gooddat)^2 + noise_peaks(i*2+1,gooddat)^2*101)^.5)
			scan = reform(noise_peaks(0,gooddat))
			ymax = max(fit_sig)
			plot, freq,fit_sig, psym=1, xtitle='Frequency (Hz)', ytitle='Peak Response (A/rt(Hz))',$
				title='Chopper response, RS'+strtrim(rss(i-1),1)+', bias '+strtrim(b,1), /ylog,/xlog, xr=[1,1000],yr=[1e-10,1e-4]
			;cols = [0,3,6]
			ntimes=round((max(scan) - min(scan))/1.e4)
			scanint = round((scan-min(scan))/1.e4)
			for j=1,ntimes+1 do begin
				scan_pts = where(scanint eq j-1)
				if scan_pts(0) ne -1 then begin
					if j gt 1 then oplot, freq(scan_pts),fit_sig(scan_pts), color=j-1, psym=1
					xyouts, 1.5*5.^(j-1),1.5e-10,'time '+strtrim(j,1), color=j-1, charsize=0.65
				endif
			endfor
;			print, 'last freqs plotted', freq(scan_pts)
;			stop
			weights = REPLICATE(1.e6, n_elements(freq))
			aaa = [1.e-5,100.]
			result = CURVEFIT(freq, fit_sig, weights, aaa, tol=1.e-12,iter=itero, $
   		                 chisq=chi, function_name='tau_fit_funct')
			aaa(1) = abs(aaa(1))
			tau_fits(0:1,i-1,b,c) = aaa
			tau_fits(2,i-1,b,c) = chi
	;		print, rss(i-1), aaa
	
			freqfit = 10^(findgen(31)/10.)
;		Old fit with sqrt in denominator
;			oplot, freqfit, aaa(0)/sqrt(1.+(freqfit/aaa[1])^2), color = 1
			oplot, freqfit, aaa(0)/sqrt(1.+(freqfit/aaa[1])^2), color = 1
			xyouts, 1.5,4e-9, 'f_3db '+string(aaa(1),format='(i4)')+' Hz', charsize=1., color=1
			xyouts, 1.5,7.5e-10, 'DC'+string(aaa(0),format='(e8.1)')+', Chi/DC^2'+string(chi/(aaa(0))^2,format='(e8.1)'), charsize=.65

			if runpr then begin
				xyouts, 1.5, 3e-5, '%R-'+string(rp(i-1,c)*100, format='(i3)')+'  P(pW)-'+string(p(i-1,c),format='(i2)')
			endif
		endif
    endif else begin
		plot, [0,1],[0,1],psym=1,title='RS'+strtrim(rss(i-1),1)
		xyouts, 0.1,0.5,'Bad chopper data'
    endelse
endfor

endfor
device,/close

endfor

tau_header=['fit data: 0-DC, 1-f_3db, 2-chi-sq','row number','bias number','column number']
save,filename=path+dir(d)+dsl+'tau_fits.sav',tau_header, tau_fits

get_lun, nf
openw, nf, path+dir(d)+dsl+'tau_fits.dat'
colstr='Column'
biasstr='Biasnum'
headstr='RS'
for c=0,ncols do begin
	for b=0,nbiases(d)-1 do begin
		colstr=colstr+' '+strtrim(c,1)+' '+strtrim(c,1)
		biasstr=biasstr+' '+strtrim(b,1)+' '+strtrim(b,1)
		headstr=headstr+' Amp Freq'
	endfor
endfor
printf,nf,colstr
printf,nf,biasstr
printf,nf,headstr
datstr = strarr(nrows)
for j=0,nrows-1 do datstr(j)= strtrim(rss(j),1)
for c=0,ncols-1 do begin
	for b=0,nbiases(d)-1 do begin
		for j=0,nrows-1 do begin
			datstr(j) = datstr(j)+' '+strtrim(tau_fits(0,j,b,c),1)+' '+strtrim(tau_fits(1,j,b,c),1)
		endfor
	endfor
endfor
for j=0,nrows-1 do printf, nf, datstr(j)
close, nf
free_lun, nf

;stop

endfor

end

;
; Fitting function for the tau_fit program
;======================
PRO tau_fit_funct, xx, aaa, ff, pder
ff    = aaa[0]/sqrt(1.+(xx/aaa[1])^2)
pder = [[1./sqrt(1.+(xx/aaa[1])^2)], $
        [aaa[0]*(xx^2/(aaa[1]^3))/((1.+(xx/aaa[1])^2)^(1.5))]]
END
