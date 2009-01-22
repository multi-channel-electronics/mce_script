pro capture_raw_average, NWRAP=nwrap, clock=clock, plotpath=plotpath

current_data = '/data/cryo/20081217/'
filebaseog='raw__bias_'
nbias=24             ;24 
bstart = 2500
bstep = 2500
psplot=1
datagen=0
summary_plot=1

nrow=33
tauest_all=fltarr(nbias,32)

nfiles=100

if keyword_set(plotpath) then plotpath=plotpath else plotpath=current_data
if psplot then begin
	set_plot, 'ps'
	device,/color
	TVLCT, [0,255,0,0,255,0,255,150,0,150,150,0], [0,0,255,0,0,255,255,0,150,150,0,150], [0,0,0,255,255,255,0,150,150,0,0,0]
endif

if datagen then begin

for bb=0,nbias-1 do begin
  bias = long(bstart) + bb*long(bstep)
  if bias lt 10000 then biasst = string(bias, format='(i4)') else biasst = string(bias, format='(i5)')
  sq2bias = lonarr(32)
  sq2bias(*) = bias
  tit = 'Summary of bandwidth measurements at SQ2 bias = '+biasst  
  filebase = filebaseog + biasst

for f=0,nfiles-1 do begin

  if f lt 10 then fnum = string(f, format='(i1)') else fnum = string(f, format='(i2)')
  file_name=filebase+'_'+fnum

  full_name = current_data + '/*' + file_name
  print,full_name
  
  d = mas_data(full_name)
  data = fltarr([32,nrow*200])
  for g= 0,199 do for r= 0,32 do data[*,g*nrow+r] = d[*,r,g]

  row_delay = 4
  fb_delay  =  6
  samp_delay = 90
  n_samp   =  10

;stop

  if f eq 0 then d_all = data $
	else for col=0,31 do d_all(col,*) = d_all(col,*) + data(col,*)

endfor

d_all = d_all/nfiles
dat_all = fltarr(n_elements(d_all(0,*)),32)
for g=0,31 do dat_all(*,g) = d_all(g,*)

;stop

if psplot then begin
set_plot, 'ps'

device, filename=plotpath + '/' + filebase + '_avg.ps', /landscape
;device, filename=plotpath + '/' + filebase + '_avg_zoom.ps', /landscape
endif

Graph_label = 'Data file is ' + full_name 

!p.multi=0
taufits=fltarr(nrow,32)

for nch = 0, 31 do begin

;  plot,  dat_all[0:*,nch],/xs,xrange=[0,5300], yticklen= 1.0,$
  plot,  dat_all[0:*,nch],/xs,xrange=[0,1000], yticklen= 1.0,$
    title = 'Series Array Channel ' + string ( nch, format='(I)')+' - '+current_data+'/'+filebase+'*',$
    xtitle='Time (clock cycles) - 100 clock cycles per row', ytitle='Output (A/D Units) '

  rowlen=100
  coffset=30
  clen=70
  minstep = 50
  minfit = 200
  for r=0,nrow-1 do begin
      pntall=indgen(rowlen-coffset)+coffset+r*rowlen
      fit_sig = reform(dat_all(pntall,nch))
      pntbeg = max(where(abs(fit_sig -fit_sig(n_elements(fit_sig)-1)) gt minstep))
      if pntbeg ne -1 and pntbeg ne 0 then begin
          if fit_sig(pntbeg) - fit_sig(pntbeg-1) gt 0 then sdir=1 else sdir=-1
          pntst = pntbeg
          pdir = sdir
          while pntst gt 1 and pdir eq sdir do begin
              pntst = pntst-1
              if fit_sig(pntst) - fit_sig(pntst-1) gt 0 then pdir=1 else pdir=-1
          endwhile
          pntst=pntst+2
          fitpnt = pntall(pntst:n_elements(pntall)-1)
;	  oplot, [fitpnt(0),fitpnt(0)],[-1e4,1e4], linestyle=1
          clen = n_elements(fitpnt)
	time=findgen(clen)
	fit_sig = reform(dat_all(fitpnt,nch))
	if max(fit_sig) - min(fit_sig) gt minfit then begin
            oplot, [fitpnt(0),fitpnt(0)],[-1e4,1e4], linestyle=1
	  	weights = findgen(clen)/clen +1.
		fitst = fit_sig(0)
		fited = fit_sig(clen-1)  
		a = [5,fitst,fited-fitst,0]
  		result = CURVEFIT(time, fit_sig, weights, a,iter=itero, $
  		    chisq=chi, function_name='exp_fit_funct', itmax=100)
		taufits(r, nch) = a(0)
;		if nch eq 1 then stop
		if psplot then oplot, fitpnt, result, linestyle=0, color=1 $
                  else oplot, fitpnt, result, linestyle=2
        endif
    endif
  endfor
;  stop
endfor   ; End plotting each channel.

;xyouts, 0., 1.02, graph_label, charsize=1.0, /normal
if psplot then begin
    device,/close

    device, filename=plotpath + '/' + filebase + '_summary.ps', /landscape
endif

plot, [0],[0], xr=[-1,32],/xs,yr=[0,50],xtitle='column number',ytitle='time constant (clock cycles)', $
	title=tit, yticklen=1
tauest = fltarr(32)
for nch = 0,31 do begin
	pt = where(taufits(*,nch) gt 0)	
	if n_elements(pt) gt 10 then begin
		oplot, replicate(nch,n_elements(pt)), taufits(pt,nch), psym=1
		tauest(nch) = median(taufits(pt,nch))
	endif
endfor
cols = indgen(32)
pt = where(tauest gt 0)
if pt(0) ne -1 then begin
    oplot, cols(pt), tauest(pt), color=1
    oplot, cols(pt), tauest(pt), color=1, psym=2
endif

xyouts, 0, 45, 'Median time constants for columns with > 15 "good" measurements', color=1, charsize=1.4

tauest_all(bb,*) = tauest

;plot, sq2bias(pt), tauest(pt), xtitle='SQ2 bias (DAC)', ytitle='time constant (clock cycles)', psym=2
;fit = linfit(sq2bias(pt), tauest(pt))
;oplot, [0,1e5],[fit(0),fit(0)+fit(1)*1e5]

save, filename=plotpath+'/'+filebase+'_taus.sav', taufits, tauest, sq2bias

if psplot then device, /close  ; Close plot file.

endfor

bias_all = findgen(nbias)*bstep+bstart

save, filename=plotpath+'/bandwidth_summary_data.sav',bias_all, tauest_all

endif

if summary_plot then begin
        restore, plotpath+'/bandwidth_summary_data.sav'
	device, filename=plotpath + '/Bandwidth_sq2bias_summary.ps', /landscape
	plot, [0],[0], xr=[0,max(bias_all)], yr=[0,40], xtitle='SQ2 bias (DAC)', ytitle='time constant (clock cycles)', $
		title='Bandwidth Measurements at different SQ2 bias currents', yticklen=1
	for i=0,31 do begin
            pt = where(tauest_all(*,i) ne 0)
            if pt(0) ne -1 then begin
		oplot, bias_all(pt), tauest_all(pt,i), color=i mod 12
		xyouts, bias_all(pt(0))-1000, tauest_all(pt(0),i)-.2, 'C'+strtrim(i,1), color=i mod 12
            endif
	endfor

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
