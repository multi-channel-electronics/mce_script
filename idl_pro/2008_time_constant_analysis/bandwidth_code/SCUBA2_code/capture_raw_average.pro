pro capture_raw_average, NWRAP=nwrap, clock=clock, plotpath=plotpath

current_data = '/jcmtdata/raw/scuba2/s8a/eng/20081021'
filebase='raw30'
bias=0

current_data = '/jcmtdata/raw/scuba2/s8a/eng/20081022'
filebase='30'
bias=1

filebase='raw40'
bias=0

filebase='raw50'
bias=0

filebase='raw60'
bias=1

filebase='raw70'
bias=2

current_data = '/jcmtdata/raw/scuba2/s8a/eng/20081023'
filebase='raw71'
bias = 3

;filebase='raw72'
;bias = 4

;filebase='raw73'
;bias = 5

;filebase='raw74'
;bias = 6

filebase='raw75'
bias = 7

;filebase='raw76'
;bias = 8

filebase='raw80'
bias = -1

;filebase='raw81'
;bias = -1

;filebase='raw82'
;bias = -1

;filebase='raw83'
;bias = -1

;filebase='raw84'
;bias = -1

;filebase='raw85'
;bias = -1

;filebase='raw86'
;bias = -1

;filebase='raw87'
;bias = -1

;filebase='raw88'
;bias = -1

;filebase='raw89'
;bias = -1

;filebase='raw90'
;bias = -1


nblocks=256  
filesuf='-eng.txt'
nfiles=50

if bias eq -1 then begin
  ; Biases selected from bandwidth measurements at all different biases on 10-23-08
  sq2bias=long([7000, 13000, 8000, 13000, 12000, 0, 0, 0, $ 
        0, 0, 22000, 0, 18000, 0, 10000, 11000, $
	8000, 0, 23000, 16000, 25000, 10000, 12000, 9000, $
	10000, 10000, 0, 6000, 0, 7000, 0, 0])
endif else begin
  if bias eq 0 then begin
	sq2bias=long([ 7000,    7000,    6000,   11000,    8000,       0,       0,       0, $ 
	     0,       0,   22000,       0,   14000,       0,    5000,    6000, $
	   6000,       0,   23000,   10000,   24000,    6000,    6000,    5000, $ 
	   6000,    6000,       0,    5000,       0,    6000,       0,       0])
	tit='Summary of bandwidth measurements with SQ2 biases at roughly Ic-max'
  endif else begin 
	if bias eq 1 then begin
		sq2bias=long([14000,    14000,    12000,   22000,    16000,       0,       0,       0, $ 
	          0,       0,   25000,       0,   25000,       0,    10000,    12000, $
		 12000,       0,   25000,   20000,   25000,    12000,    12000,    10000, $
	        12000,    12000,       0,    10000,       0,    12000,       0,       0])
		tit='Summary of bandwidth measurements with SQ2 biases near twice Ic-max'
	endif else begin 
		if bias eq 2 then begin
			sq2bias=long([28000,    28000,    24000,   30000,    30000,       0,       0,       0, $ 
	        		  0,       0,   30000,       0,   30000,       0,    20000,    24000, $
				 24000,       0,   30000,   30000,   30000,    24000,    24000,    20000, $
	        		24000,    24000,       0,    20000,       0,    24000,       0,       0])
		  	tit='Summary of bandwidth measurements with SQ2 biases near 4*Ic-max'
		endif else begin
			sq2bias=long([ 7000,    7000,    6000,   11000,    8000,       0,       0,       0, $ 
			     0,       0,   22000,       0,   14000,       0,    5000,    6000, $
			   6000,       0,   23000,   10000,   24000,    6000,    6000,    5000, $ 
			   6000,    6000,       0,    5000,       0,    6000,       0,       0])
			tit='Summary of bandwidth measurements with SQ2 biases at > Ic-max'
			sq2on = where(sq2bias ne 0)
			sq2bias(sq2on) = sq2bias(sq2on)+2000.*(bias-2)
			sq2max = where(sq2bias gt 30000)
			if sq2max(0) ne -1 then sq2bias(sq2max) = 30000
		endelse
	endelse
  endelse
endelse

for f=0,nfiles-1 do begin

  if f lt 10 then fnum = '0'+string(f, format='(i1)') else fnum = string(f, format='(i2)')
  file_name=filebase+fnum+filesuf

  full_name = current_data + '/' + file_name
  print,full_name
  openr,1,full_name

  row_delay = 4
  fb_delay  =  6
  samp_delay = 80
  n_samp   =  48

  rd =findgen(row_delay)
  fd = findgen(fb_delay)
  sd  = findgen(samp_delay)
  nsamp = findgen(samp_delay+n_samp)

  length = nblocks*41
  data = fltarr(length,32)
  block = fltarr(32,41)
  header = intarr(43)

  for n=0, nblocks-1 do begin

  ; Read one 8x41 block.

	start = n*41
	stop = start+40
	readf, 1, header
	readf, 1, block

  ; Write current block into DATA

 	for m = start, stop do begin
	     data[m,*]= block[*,m-start]
 	endfor     ;End of writing current block

 	readf,1, checksum   ; Discard.

  endfor      ;  End of reading all the blocks in the input file.
  close, 1     ; Close input file.


  if f eq 0 then dat_all = data $
	else for col=0,31 do dat_all(*,col) = dat_all(*,col) + data(*,col)

endfor

dat_all = dat_all/nfiles

set_plot, 'ps'

if keyword_set(plotpath) then plotpath=plotpath $
	else plotpath=current_data
device, filename=plotpath + '/' + filebase + '_avg.ps', /landscape
;device, filename=plotpath + '/' + filebase + '_avg_zoom.ps', /landscape
device,/color
TVLCT, [0,255,0,0,255,0,255,150,0,150,150,0], [0,0,255,0,0,255,255,0,150,150,0,150], [0,0,0,255,255,255,0,150,150,0,0,0]

Graph_label = 'Data file is ' + full_name 

;
; Fix data sign.  Data are recorded as sign + 7 bits, written to disc
; as 8 bits.
;

if not keyword_set(nwrap) then begin

here = where (data gt 127.)

if here[0] ne -1 then  data[here]=  data[here] -256

there = where (data lt -127.)
if there[0] ne -1 then  data[there]= -256 - data[there]

end       ; end fixing sign in the data.



!p.multi=[0,0,0]
taufits=fltarr(41,32)

for nch = 0, 31 do begin

  plot,  dat_all[0:*,nch],/xs,xrange=[0,5300], yticklen= 1.0,$
;  plot,  dat_all[0:*,nch],/xs,xrange=[0,1000], yticklen= 1.0,$
    title = 'Series Array Channel ' + string ( nch, format='(I)')+' - '+current_data+'/'+filebase+'*',$
    xtitle='Time (clock cycles) - 128 clock cycles per row', ytitle='Output (A/D Units) '

  coffset=32
  clen=105
  for r=0,40 do begin
	oplot, [r*128+coffset,r*128+coffset],[-1e4,1e4], linestyle=1
	pnt=coffset+r*128+indgen(clen)
	time=findgen(clen)
	fit_sig = reform(dat_all(pnt,nch))
	if max(fit_sig) - min(fit_sig) gt 100 then begin
	  	weights = findgen(clen)/clen +1.
		fitst = fit_sig(0)
		fited = fit_sig(clen-1)  
		a = [5,fitst,fited-fitst,0]
  		result = CURVEFIT(time, fit_sig, weights, a,iter=itero, $
  		    chisq=chi, function_name='exp_fit_funct', itmax=100)
		taufits(r, nch) = a(0)
;		if nch eq 10 then stop
		oplot, pnt, result, linestyle=0, color=1
	endif
  endfor
endfor   ; End plotting each channel.

;xyouts, 0., 1.02, graph_label, charsize=1.0, /normal
device,/close

device, filename=plotpath + '/' + filebase + '_summary.ps', /landscape

plot, [0],[0], xr=[-1,32],/xs,yr=[0,50],xtitle='column number',ytitle='time constant (clock cycles)', $
	title=tit, yticklen=1
tauest = fltarr(32)
for nch = 0,31 do begin
	pt = where(taufits(*,nch) gt 0)	
	if n_elements(pt) gt 15 then begin
		oplot, replicate(nch,n_elements(pt)), taufits(pt,nch), psym=1
		tauest(nch) = median(taufits(pt,nch))
	endif
endfor
cols = indgen(32)
pt = where(tauest gt 0)
oplot, cols(pt), tauest(pt), color=1
oplot, cols(pt), tauest(pt), color=1, psym=2

xyouts, 0, 45, 'Median time constants for columns with > 15 "good" measurements', color=1, charsize=1.4

;plot, sq2bias(pt), tauest(pt), xtitle='SQ2 bias (DAC)', ytitle='time constant (clock cycles)', psym=2
;fit = linfit(sq2bias(pt), tauest(pt))
;oplot, [0,1e5],[fit(0),fit(0)+fit(1)*1e5]

save, filename=plotpath+'/'+filebase+'_taus.sav', taufits, tauest, sq2bias

device, /close  ; Close plot file.

if 0 then begin
	restore, '~/plots/20081022/raw60_taus.sav'
	b60 = sq2bias
	tau60 = tauest
	restore, '~/plots/20081022/raw70_taus.sav'
	b70 = sq2bias
	tau70 = tauest
	restore, '~/plots/20081022/raw50_taus.sav'

	device, filename=plotpath + '/Bandwidth_sq2bias_summary.ps', /landscape
	plot, [0],[0], xr=[0,25000], yr=[0,20], xtitle='SQ2 bias (DAC)', ytitle='time constant (clock cycles)', $
		title='Bandwidth Measurements at different SQ2 bias currents'
	for i=0,31 do begin
		oplot, [sq2bias(i), b60(i)], [tauest(i),tau60(i)], color=i mod 12
		xyouts, sq2bias(i)-1000, tauest(i)-.2, 'C'+strtrim(i,1), color=i mod 12
	endfor
	restore, '~/plots/20081022/30_taus.sav'
	b60 = sq2bias
	tau60 = tauest
	restore, '~/plots/20081022/raw40_taus.sav'
	for i=0,31 do begin
		oplot, [sq2bias(i), b60(i)], [tauest(i),tau60(i)], color=i mod 12, linestyle=2
		xyouts, sq2bias(i)-1000, tauest(i)-.2, 'C'+strtrim(i,1), color=i mod 12
	endfor
	xyouts, 10000, 18, 'Solid - low oscillation 20081022 day measurements'
	xyouts, 10000, 17, 'Dashed - high oscillation 20081021 night measurements'
	device, /close

	device, filename=plotpath + '/Bandwidth_sq2bias_summary2.ps', /landscape
	plot, [0],[0], xr=[0,30000], yr=[0,20], xtitle='SQ2 bias (DAC)', ytitle='time constant (clock cycles)', $
		title='Bandwidth Measurements at different SQ2 bias currents'
	for i=0,31 do begin
		oplot, [sq2bias(i), b60(i), b70(i)], [tauest(i),tau60(i),tau70(i)], color=i mod 12
		xyouts, sq2bias(i)-1000, tauest(i)-.2, 'C'+strtrim(i,1), color=i mod 12
	endfor
	xyouts, 10000, 18, 'Solid - low oscillation 20081022 day measurements'
	device,/close
endif
stop
end


PRO exp_fit_funct, xx, a, ff, pder
ff    = a(1)+a(2)*(1 - exp(-(xx+a(3))/a(0)))

pder  = [[(-1)*a(2)*(xx+a(3))/a(0)^2*exp(-(xx+a(3))/a(0))], $
	[replicate(1.,n_elements(xx))], $
	[(1 - exp(-(xx+a(3))/a(0)))], $
	[a(2)/a(0)*exp(-(xx+a(3))/a(0))]]

END  
