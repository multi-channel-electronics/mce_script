pro capture_raw_summary_450

plotpath='~/plots/20081126/'
sq2bs = fltarr(5,32)
taus = fltarr(5,32)


restore, '~/plots/20081126/raw1_taus.sav'
sq2bs(0,*) = sq2bias(*)
taus(0,*) = tauest
restore, '~/plots/20081126/raw2_taus.sav'
sq2bs(1,*) = sq2bias(*)
taus(1,*) = tauest
restore, '~/plots/20081126/raw3_taus.sav'
sq2bs(2,*) = sq2bias(*)
taus(2,*) = tauest
restore, '~/plots/20081126/raw4_taus.sav'
sq2bs(3,*) = sq2bias(*)
taus(3,*) = tauest
restore, '~/plots/20081126/raw5_taus.sav'
sq2bs(4,*) = sq2bias(*)
taus(4,*) = tauest


set_plot, 'ps'
device,/color
TVLCT, [0,255,0,0,255,0,255,150,0,150,150,0], [0,0,255,0,0,255,255,0,150,150,0,150], [0,0,0,255,255,255,0,150,150,0,0,0]

device, filename=plotpath + '/Bandwidth_450_sq2bias_total_summary.ps', /landscape
plot, [0],[0], xr=[0,30000], yr=[0,25], xtitle='SQ2 bias (DAC)', ytitle='time constant (clock cycles)', $
	title='450 array Bandwidth Measurements at different SQ2 bias currents, 20081126'
for i=0,31 do begin
	pt = sort(sq2bs(*,i))
	gd=where(taus(pt,i) gt 0)
	if gd(0) ne -1 then begin
		oplot, sq2bs(pt(gd),i), taus(pt(gd),i), color=i mod 12
		oplot, sq2bs(pt(gd),i), taus(pt(gd),i), color=i mod 12, psym=7, symsize=0.5
		xyouts, sq2bs(pt(gd(0)),i)-1000, taus(pt(gd(0)),i)-.2, 'C'+strtrim(i,1), color=i mod 12
		print, 'Column', i, sq2bs(pt(gd(where(taus(pt(gd),i) eq min(taus(pt(gd),i))))),i), min(taus(pt(gd),i))
	endif
endfor
;xyouts, 10000, 18, 'Solid - low oscillation 20081022 day measurements'
;xyouts, 10000, 17, 'Dashed - high oscillation 20081021 night measurements'
device, /close


stop
end

