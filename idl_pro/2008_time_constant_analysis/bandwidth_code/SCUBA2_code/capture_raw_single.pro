pro raw_capture_single, file_name, nch, t_start, t_stop, NUMBERS = numbers


nblocks=128
full_name = '/data/cryo/current_data/' + file_name
openr, 1, full_name

length = nblocks*41
data = fltarr(length,8)
block = fltarr(8,41)
header = ''

for n=0, nblocks-1 do begin

start = n*41
stop = start+40
readf, 1, header
readf, 1, block
;print, block

  for m = start, stop do begin
     data[m,*]= block[*,m-start]
 endfor
 ;print, 'Row:', start, ' DATA:', data[start] 
readf,1, checksum

;read, pause
;print,'Row: ',n ,'Checksum=', checksum
endfor


close, 1

set_plot, 'ps'

device, filename='/data/cryo/current_data/analysis/' + file_name + 'single.ps', /landscape

here = where (data gt 127.)
 
data[here]= 128 - data[here]



there = where (data lt -127.)
 
data[here]= -128 - data[here]

a= replicate( 0., 64)
b=replicate(1, 64)

address_cycle = fltarr(128)
address_cycle[0:63]=a
address_cycle[64:*]=b

address_clock = fltarr(length)

for m=0,40 do begin
address_clock[m*128: m*128+127] = address_cycle
endfor

t_label = (findgen(41)+.3)*64.*20.
chlabel = strarr(41) 


!p.multi =0


time = findgen(length)* 20  ; ns
here = where( time gt t_start and time lt t_stop )

min_plot = min(data[here,nch])
max_plot = max(data[here,nch])
h_label = min_plot - (max_plot - min_plot)/10.

plot, time[here],data[here,nch], /xs, thick=4, title=' Response to Address Card',$
   xtitle='Time (ns)'  
oplot, time,(address_clock - .5)*200, linestyle=1
oplot,  time[here],data[here,nch], psym=1, symsize=0.5

if keyword_set(numbers) then begin

  for n_addr=0, 40 do begin
  chlabel[n_addr] = string(n_addr, format='(i2)')
  xyouts , t_label[n_addr], h_label, chlabel[n_addr], charsize=0.7

endfor

endif 


device, /close


end
