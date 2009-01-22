   pro raw_rf_search, FNAME=fname

; M halpern   19 Dec 2008  
;  Program to read in 50MHz data files, expected to contain 8192
;  readings, and to look for spikes in range few kHz to 25 MHz.

;dir = '/data/cryo/20081217/'
dir = '/data/cryo/current_data/'

;fname=''

datafile=dir+fname
peak_filename=datafile+'rfpeaks.txt'

openw, 1, peak_filename

d=mas_data(datafile)

; Should return an array [32,33,249]
npts= 33*249

data=reform(d, 32, npts)

; Get plotting going.

set_plot, 'ps'
device, /landscape
device, xsize=25., ysize=18., xoffset=0., yoffset=0.

device, filename='/home/mce/halpern/plots/'+fname+'_rf.ps'

!p.multi=[0,1,2]
freq= findgen(4096)*25./4096.  ; freq scale for plotting ffts



for n_rc=0, 3 do begin

combo=fltarr(8192)

j= 8*n_rc
k=j+7

for m=0, 8191 do begin

combo[m]=total(data[j:k,m])
endfor
combo=combo/8

plot, combo, /ynozero,/xs,$
  title='!6'+datafile+' Columns summed',$
  xtitle='!6 Time (50 MHz Clock Cycles)',$
  ytitle='!6 ADC Units', charsize=1.1

; FInd peaks:

t_series = combo - mean(combo)

peaks=intarr(5)
pk_ind=intarr(5)

for npk=0,4 do begin

  peaks[npk] = max(abs(t_series), pk_i)
 if pk_i lt 100 then pk_i = 100
 if pk_i gt 8000 then pk_i = 8091

  t_series[pk_i-100:pk_i+100]=0
  pk_ind[npk]=pk_i
endfor

order=sort(pk_ind)

printf, 1, 'Readout Card ', string(n_rc, format='(i3)'), 'Clock numb.s and Peak heights'
printf, 1, pk_ind[order]
printf, 1, peaks[order]



spec=abs(fft(combo))

; Smooth for plotting.
smspec=spec

smspec[500:*]=smooth(smspec[500:*],2)
smspec[800:*]=smooth(smspec[800:*],2)
smspec[1000:*]=smooth(smspec[1000:*],2)
smspec[1500:*]=smooth(smspec[1500:*],2)
smspec[2000:*]=smooth(smspec[2000:*],2)
smspec[3000:*]=smooth(smspec[3000:*],2)


plot, freq[1:4095], smspec[1:4095], /xlog, /ylog,/xs

endfor




close, 1
device,/close

end

