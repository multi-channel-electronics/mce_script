pro capture_raw_plot_window, file_name, NWRAP=nwrap, clock=clock

nblocks=128  
full_name = '/data/cryo/current_data/' + file_name

openr, 1, full_name

length = nblocks*41
data = fltarr(length,8)
block = fltarr(8,41)
header = ''

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

;set_plot, 'ps'

;device, filename='/data/cryo/current_data/analysis/' $ 
;                    + file_name + '.ps', /landscape

current_data_name=''
openr, 3, '/data/cryo/current_data_name'
readf, 3, current_data_name
close, 3

Graph_label = 'Data file is /data/cryo/' $ 
       + current_data_name +'/' +  file_name

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

; Make a square wave to show 64pt address clock.

a= replicate( 0., 64)
b=replicate(1, 64)
address_cycle = fltarr(128)
address_cycle[0:63]=a
address_cycle[64:*]=b

address_clock = fltarr(length)

for m=0,40 do begin
address_clock[m*128: m*128+127] = address_cycle
endfor

;!p.multi=[0,2,4]

;for nch = 0,7 do begin
for nch=5,5 do begin

plot,  data[4480:4608,nch], /xs, $
  title = 'Series Array Channel ' + string ( nch, format='(I)'),$
  xtitle='Time (clock cycles)', ytitle='Output (A/D Units) '
if keyword_set(clock) then oplot, (address_clock - .5)*200


endfor   ; End plotting each channel.

!p.multi=1

xyouts, 0., 1.02, graph_label, charsize=1.0, /normal


;device, /close  ; Close plot file.

stop
end
