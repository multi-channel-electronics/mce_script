pro capture_raw_plot, file_name, NWRAP=nwrap, clock=clock, plotpath=plotpath

nblocks=256  
current_data = getenv('CURRENTDATADIR')
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

set_plot, 'ps'

if keyword_set(plotpath) then plotpath=plotpath $
	else plotpath=current_data
device, filename=plotpath + '/' $ 
                    + file_name + '.ps', /landscape

current_data_name=''
;openr, 3, '/data/cryo/current_data_name'
;readf, 3, current_data_name
;close, 3

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

; Make a square wave to show 64pt address clock.



!p.multi=[0,0,0]

c1=0

for nch = c1, c1+31 do begin

plot,  data[0:*,nch],/xs,xrange=[0,1000], ticklen= 1.0,$
  title = 'Series Array Channel ' + string ( nch, format='(I)'),$
  xtitle='Time (clock cycles)', ytitle='Output (A/D Units) '

;oplot, rd, -120, linestyle=1
;oplot, fd, -110, linestyle=1
;oplot, sd, -110, linestyle=1
;oplot, nsamp, -110, linestyle=0.5

c1++
endfor   ; End plotting each channel.

xyouts, 0., 1.02, graph_label, charsize=1.0, /normal


device, /close  ; Close plot file.


end
