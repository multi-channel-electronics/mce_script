pro auto_setup_iv_plot, COLUMN=column, ROW=row,RC=rc,file_name,BINARY=binary,nodasscript=nodasscript,interactive=interactive,tes_heater=tes_heater

;if not keyword_set(numrows) then numrows=41

close,/all

bitpart=14

data_mode=4

npts=2000

if not keyword_set(nodasscript) then begin
  if not keyword_set(RC) then begin
    print,'If you want to run the shell script you should specify the read-out card number!!'
    goto, fine
  endif
  if not keyword_set(tes_heater) then begin
    ;spawn,'read_status'+' '+strcompress('rc'+ string(rc),/REMOVE_ALL)+' '+file_name
    spawn,'ramp_tes_bias '+file_name+' '+string(rc)
  endif else begin
    ;spawn,'read_status'+' '+strcompress('rc'+ string(rc),/REMOVE_ALL)+' '+file_name
    spawn,'ramp_tes_bias '+file_name+' '+string(rc)+' '+string(tes_heater)
  endelse
endif

stop

default_date = 'current_data/'
date= default_date

current_data='/data/cryo/' + date + '/'

full_name = current_data + file_name
plot_name = current_data+ 'analysis/' + file_name 

col_name =''
row_name = ''

;need some info
;full_name = current_data + file_name + '.iv'
openr, 1, full_name
header = lonarr(43)
line=''
;repeat readf,1,line until strmid(line,4,9) eq "data_mode"
;data_mode=string(line)
;repeat readf,1,line until strmid(line,0,11) eq "string(1) step size"
;close, 1

;for i=0,9 do readf,1,line

;full_name = current_data + file_name + '.iv'
;openr, 1, full_name
if n_elements(binary) eq 0 then begin
	readf, 1, header
endif else begin
	;for a binary file
	readu, 1, header
endelse

;f_samp=1./(0.00000002*header(39)*header(40)*header(41))	;old firmware
f_samp=1./(0.00000002*header(2)*header(3)*header(4))
;numrows=header(41)	;old firmware
numrows=header(3)	
close, 1

openr, 1, full_name
block=dblarr(8,numrows)
blockbin=lonarr(8,numrows)
blockbincol=lonarr(8)
data = dblarr(npts,8,numrows)
databin = lonarr(npts,8,numrows)

;checksum=intarr(1)

!p.multi=[0,4,2]

if n_elements(column) eq 0 then begin
  cmin=0
  cmax=7
endif else begin
  cmin=column
  cmax=column
  !p.multi=[0,1,2] 
  col_name = 'c'+ string(column, format='(i1)')
print, col_name ; TEST
endelse

if n_elements(row) eq 0 then begin
  rmin=0
  rmax=numrows-1
endif else begin
  rmin=row
  rmax=row
  !p.multi=[0,1,2]
  ;row_name =  'r'+ string(row, format='(i1)')
  row_name =  strcompress('r'+ string(row),/REMOVE_ALL)
print, row_name ; TEST
endelse

plot_name = plot_name+'_' + col_name + row_name + '.ps'
print, plot_name

line=''
;repeat readf,1,line until strmid(line,4,9) eq "data_mode"
;data_mode=string(line)
;repeat readf,1,line until strmid(line,0,10) eq "end_status"
;for i=0,9 do readf,1,line
set_plot, 'ps'
device, /landscape, xsize=25., ysize=17.
device, filename=plot_name

m=0

while not eof(1) and m lt npts do begin

if n_elements(binary) eq 0 then begin
	readf, 1, header
endif else begin
	;for a binary file
	readu, 1, header
endelse

;print,'numero righe',header(41)

;f_samp=1./(0.00000002*header(2)*header(3)*header(4))


if n_elements(binary) eq 0 then begin
	readf, 1, block
	data[m,*,*]= block
	readf,1, datum
endif else begin
	;for a binary file
	;readu, 1, blockbin
	;databin[m,*,*]= blockbin
	for i=0,numrows-1 do begin
		readu, 1, blockbincol
		databin[m,*,i]= blockbincol
	endfor
	readu,1, datum
endelse

m=m+1

endwhile

close, 1

;for a binary file
if n_elements(binary) ne 0 then data=databin

; Trim data array to actual input length.
data= data[0:m-1,*,*]

npts = m   ; set npts to actual number of  frames read.

;stop

error=data
fb=data
fb=floor(data/2.^bitpart)
error=abs(floor(data-fb*2.^bitpart))

!p.multi=[0,2,2]
	
for n_row = rmin, rmax  do begin

  	for n_col = cmin, cmax do begin
		;stop
   		print, 'C ', n_col, 'R ', n_row, 'error: ', error[0:9,n_col, n_row]
                for i=0,npts-1 do begin
			if error(i,n_col,n_row) ge 2.^(bitpart-1) then error(i,n_col,n_row)=-(2.^bitpart-error(i,n_col,n_row))
		endfor
		;stop
     		plot, error[*,n_col, n_row], /ynozero, thick=4,title='error'; , yrange=[-35000., -40000.]
                towrite='st. dev.'+string(stddev(error[*,n_col, n_row]))
		xyouts,npts/4.,max(error[*,n_col, n_row]),towrite
		spec = abs(fft(error[*, n_col, n_row]))

		;f_max = 500.  ; What a hack!  MH  17 Nov 05.
		nf = n_elements(spec)/2
		freq =(1./nf)* findgen(nf)* f_samp/2.
		plot, freq[2:nf-1],spec[2:nf-1], /ylog, /xlog , thick=4,xtickinterval=100,ticklen=1,ytitle='fft error'; , yrange=[0.1, 1000.]
		maxspec=max(spec[2:nf-1],ind)
		maxfreq=freq[2+ind]
		towrite='max='+string(maxspec)+' @'+string(maxfreq)+'Hz'
		xyouts,freq[5],maxspec,towrite
                xyouts,-max(freq),maxspec*10.,plot_name
		oplot, [60.,60.], [1., 1000.], linestyle=1, thick=3

		if n_row eq rmin then begin
			print, max(spec(2:nf-1))
		endif

		print, 'C ', n_col, 'R ', n_row, 'fb: ', fb[0:9,n_col, n_row]
     		plot, fb[*,n_col, n_row], /ynozero, thick=4,title='fb'; , yrange=[-35000., -40000.]
		towrite='st. dev.'+string(stddev(fb[*,n_col, n_row]))
		xyouts,npts/4.,max(fb[*,n_col, n_row]),towrite
		spec = abs(fft(fb[*, n_col, n_row]))

		;f_max = 500.  ; What a hack!  MH  17 Nov 05.
		nf = n_elements(spec)/2
		freq =(1./nf)* findgen(nf)* f_samp/2.
		plot, freq[2:nf-1],spec[2:nf-1], /ylog , /xlog, thick=4,xtickinterval=100,ticklen=1,ytitle='fft fb'; , yrange=[0.1, 1000.]
		maxspec=max(spec[2:nf-1],ind)
		maxfreq=freq[2+ind]
		towrite='max='+string(maxspec)+' @'+string(maxfreq)+'Hz'
		xyouts,freq[5],maxspec,towrite
		oplot, [60.,60.], [1., 1000.], linestyle=1, thick=3

		if n_row eq rmin then begin
			print, max(spec(2:nf-1))
		endif

		xyouts, 0.0*(!D.X_SIZE), 1.00*(!D.Y_SIZE), data_mode, /device
   	endfor               ; end column loop
endfor    ;   end row loop    


device, /close

if keyword_set(interactive) then spawn,'ggv '+plot_name+' &'

print,' '
print,'###########################################################################'
print,' '
print,'To view the the frame_test_plot curves check the file '+string(plot_name)
print,' '
print,'###########################################################################'



fine:

end
