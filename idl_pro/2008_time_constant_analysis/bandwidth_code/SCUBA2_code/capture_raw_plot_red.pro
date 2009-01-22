pro capture_raw_plot_red, file_name, NWRAP=nwrap, clock=clock

close,/all

nblocks=128  
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

blksize=34
rn=10


length = nblocks*blksize
data = fltarr(length,32)
block = fltarr(32,blksize-1)
header = intarr(43)
data_red=fltarr(nblocks*rn,32)

for n=0, nblocks-1 do begin

; Read one 8x41 block.

start = n*blksize
start_red=n*rn
;stop = start+31
stop= start+blksize-2
stop_red=start_red+rn-1
readf, 1, header

;print,header

readf, 1, block

;print,block(*,0)

; Write current block into DATA

 for m = start, stop do begin
     data[m,*]= block[*,m-start]
 endfor     ;End of writing current block

for col=0,31 do begin
	data_red(start_red:stop_red,col)=data(start:start+rn-1,col)
endfor

;stop

readf,1, checksum   ; Discard.


;stop
endfor      ;  End of reading all the blocks in the input file.


close, 1     ; Close input file.

data=data_red

;stop

set_plot, 'ps'

device, filename=current_data + '/' $ 
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



!p.multi=[0,2,4]

read, 'Start at which column?', c1

s=size(data)

for nch = c1, c1+1 do begin

plot,  data[0:*,nch],/xs,xrange=[0,s(1)],yrange=[min(data(0:*,nch)),max(data(0:*,nch))],ticklen= 1.0,$
  title = 'Series Array Channel ' + string ( nch, format='(I)'),$
  xtitle='Time (clock cycles)', ytitle='Output (A/D Units) '

;oplot, rd, -120, linestyle=1
;oplot, fd, -110, linestyle=1
;oplot, sd, -110, linestyle=1
;oplot, nsamp, -110, linestyle=0.5


endfor   ; End plotting each channel.

xyouts, 0., 1.02, graph_label, charsize=1.0, /normal


device, /close  ; Close plot file.

stop

end
