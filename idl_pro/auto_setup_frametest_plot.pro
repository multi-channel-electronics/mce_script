pro auto_setup_frametest_plot, COLUMN=column, ROW=row,RC=rc,file_name,BINARY=binary,interactive=interactive,nodasscript=nodasscript,noheader=noheader, npts=npts

;if not keyword_set(numrows) then numrows=41

stpt=1000
if keyword_set(npts) then npts=npts else npts=200;1435406 ;npts=number of data points, 1 point = 0.0025s
numcol=8
coloffset=(rc-1)*8

print,'DATA MODE IS HARD-CODED in FRAMETEST PLOT!!!!!'
data_mode='4'	;'6'
if data_mode eq '4' then bitpart=14 else bitpart=0

rcdatamode=rc

if rc eq 5 then begin 
        numcol=32
        coloffset=0
        rc='s'
        rcdatamode='a'
endif 

ctime=string(file_name,format='(i10)')

if not keyword_set(nodasscript) then begin
	auto_setup_command,'wb rc'+strcompress(string(rcdatamode),/REMOVE_ALL)+' data_mode '+data_mode
        user_status = auto_setup_userword(rcdatamode)
	;spawn,'mce_cmd -q -x wb rc'+strcompress(string(RC),/REMOVE_ALL)+' data_mode '+data_mode
	spawn,'mce_run '+file_name+string(npts)+' '+string(rc),exit_status=status18
        reg_status = auto_setup_register(ctime, 'data', getenv('MAS_DATA')+file_name, npts)

	if status18 ne 0 then begin
        	print,''
        	print,'###################################################################'
        	print,'# ERROR! AN ERROR HAS OCCURED WHEN TAKING A SAMPLE OF DATA SCRIPT #'
        	print,'###################################################################'
        	print,''
        	exit,status=18
	endif
endif

default_date = 'current_data/'
date= default_date

current_data='/data/cryo/' + date + '/'

full_name = current_data + file_name
plot_name = current_data+ 'analysis/' + file_name 

;new_file_name=file_name
;openr, 1, full_name+'.name'
;readf, 1, new_file_name
;close,1

ftemp = file_search(full_name+'*')
if n_elements(ftemp) gt 2 then full_name = ftemp(1) else full_name = ftemp(0)
dotrun=ftemp(n_elements(ftemp)-1)

;newfull_name=''
;newdotrun=''

;newfull_name=strmid(full_name,0,54)
;newdotrun=newfull_name+'.run

;spawn,'mv '+full_name+' '+newfull_name
;spawn,'mv '+dotrun+' '+newdotrun

;full_name=newfull_name
;dotrun=newdotrun

;full_name = current_data + new_file_name
col_name =''
row_name = ''

;need some info

openr, 1, full_name
header = lonarr(43)
line=''
;if not keyword_set(noheader) then begin
;	repeat readf,1,line until strmid(line,4,9) eq "data_mode"
;	data_mode=string(line)
;	repeat readf,1,line until strmid(line,0,10) eq "end_status"
;endif
if n_elements(binary) eq 0 then begin
	readf, 1, header
endif else begin
	;for a binary file
	readu, 1, header
endelse
close,1

openr, 1, dotrun
repeat readf,1,line until strmid(line,0,17) eq "<RB cc data_rate>"
data_rate=fix(strmid(line,18,8))
close,1
openr, 1, dotrun
repeat readf,1,line until strmid(line,0,16) eq "<RB sys row_len>"
row_length=fix(strmid(line,17,8))
close,1
openr, 1, dotrun
repeat readf,1,line until strmid(line,0,25) eq "<RB cc num_rows_reported>"
numrows=fix(strmid(line,26,8))
close,1
openr, 1, dotrun
repeat readf,1,line until strmid(line,0,17) eq "<RB sys num_rows>"
numrows_mux=fix(strmid(line,18,8))
close,1

f_samp=1./(0.00000002*row_length*numrows_mux*data_rate)
;stop
openr, 1, full_name
block=dblarr(numcol,numrows)
blockbin=lonarr(numcol,numrows)
blockbincol=lonarr(numcol)
data = dblarr(npts,numcol,numrows)
databin = lonarr(npts,numcol,numrows)
pixel_flag=intarr(numcol,numrows)
pixel_flag(*,*)=1
pixel_flag_fb=intarr(numcol,numrows)
pixel_flag_fb(*,*)=1

;checksum=intarr(1)

!p.multi=[0,4,2]

if n_elements(column) eq 0 then begin
  cmin=0
  cmax=numcol-1
endif else begin
  cmin=column
  cmax=column
  !p.multi=[0,1,2] 
  col_name = 'c'+ string(column, format='(i1)')
;print, col_name ; TEST
endelse

;if n_elements(row) eq 0 then begin
  rmin=0
  rmax=numrows-1
;endif else begin
;  rmin=row
;  rmax=row
  !p.multi=[0,1,2]
  ;row_name =  'r'+ string(row, format='(i1)')
  row_name ='';  strcompress('r'+ string(row),/REMOVE_ALL)
;print, row_name ; TEST
;endelse

pixel_flag_name=plot_name+'_pixel_flag.ps'
plot_name = plot_name + '.ps'

print, plot_name

line=''
;repeat readf,1,line until strmid(line,4,9) eq "data_mode"
;data_mode=string(line)
;if not keyword_set(noheader) then begin
;	repeat readf,1,line until strmid(line,0,10) eq "end_status"
;endif

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

;stop

endwhile

close, 1

;for a binary file
if n_elements(binary) ne 0 then data=databin

; Trim data array to actual input length.
data= data[0:m-1,*,*]

npts = m   ; set npts to actual number of  frames read.

error=data
fb=data
fb=floor(data/2.^bitpart)
error=abs(floor(data-fb*2.^bitpart))

;error calculation for the whole array
for n_row=0,numrows-1 do begin
	for n_col=cmin,cmax do begin
		for i=0,npts-1 do begin
			if error(i,n_col,n_row) ge 2.^(bitpart-1) then error(i,n_col,n_row)=-(2.^bitpart-error(i,n_col,n_row))
		endfor
		if abs(mean(error[*,n_col, n_row])) gt abs(2.*stddev(error[*,n_col, n_row])) then pixel_flag(n_col,n_row)=0
		if total(fb[0:9,n_col, n_row]) eq 0 then pixel_flag_fb(n_col,n_row)=0
	endfor
endfor

!p.multi=[0,2,2]
	
for n_row = rmin, rmax  do begin
  	for n_col = cmin, cmax do begin
		;stop
   		;print, 'C ', n_col, 'R ', n_row, 'error: ', error[0:9,n_col, n_row]
;                for i=0,npts-1 do begin
;			if error(i,n_col,n_row) ge 2.^(bitpart-1) then error(i,n_col,n_row)=-(2.^bitpart-error(i,n_col,n_row))
;		endfor
		;stop
     		plot, error[*,n_col, n_row], /ynozero, thick=4,title='error Col '+strtrim(n_col,1)+' RS '+strtrim(n_row,1); , yrange=[-35000., -40000.]
                towrite='st. dev.'+string(stddev(error[*,n_col, n_row]))
		xyouts,npts/4.,max(error[*,n_col, n_row]),towrite
		spec = abs(fft(error[*, n_col, n_row]))

		nf = n_elements(spec)/2
		freq =(1./nf)* findgen(nf)* f_samp/2.
		plot, freq[2:nf-1],spec[2:nf-1], /ylog, /xlog , thick=4,xtickinterval=100,ticklen=1,ytitle='fft error'; , yrange=[0.1, 1000.]
		maxspec=max(spec[2:nf-1],ind)
		maxfreq=freq[2+ind]
		towrite='max='+string(maxspec)+' @'+string(maxfreq)+'Hz'
		xyouts,freq[5],maxspec,towrite
                xyouts,-max(freq),maxspec*10.,plot_name
		oplot, [60.,60.], [1., 1000.], linestyle=1, thick=3

		;if n_row eq rmin then begin
		;	print, max(spec(2:nf-1))
		;endif

		;print, 'C ', n_col, 'R ', n_row, 'fb: ', fb[0:9,n_col, n_row]
     		plot, fb[*,n_col, n_row], /ynozero, thick=4,title='fb'; , yrange=[-35000., -40000.]
		towrite='st. dev.'+string(stddev(fb[*,n_col, n_row]))
		xyouts,npts/4.,max(fb[*,n_col, n_row]),towrite
		spec = abs(fft(fb[*, n_col, n_row]))

		nf = n_elements(spec)/2
		freq =(1./nf)* findgen(nf)* f_samp/2.
		plot, freq[2:nf-1],spec[2:nf-1], /ylog , /xlog, thick=4,xtickinterval=100,ticklen=1,ytitle='fft fb'; , yrange=[0.1, 1000.]
		maxspec=max(spec[2:nf-1],ind)
		maxfreq=freq[2+ind]
		towrite='max='+string(maxspec)+' @'+string(maxfreq)+'Hz'
		xyouts,freq[5],maxspec,towrite
		oplot, [60.,60.], [1., 1000.], linestyle=1, thick=3

		;if n_row eq rmin then begin
		;	print, max(spec(2:nf-1))
		;endif

		xyouts, 0.0*(!D.X_SIZE), 1.00*(!D.Y_SIZE), data_mode, /device
   	endfor               ; end column loop
endfor    ;   end row loop    
		
device, /close

!p.multi=[0,1,1]

;plot of good pixels
set_plot, 'ps'
device, /landscape, xsize=25., ysize=17.
device, filename=pixel_flag_name
device, /color
TVLCT, [0,255,0,0,255,0,150,150], [0,0,255,0,0,255,255,0], [0,0,0,255,255,255,150,150]
;contour,pixel_flag,/fill,xr=[cmin,cmax],yr=[0,numrows-1],xst=1,yst=1,xtitle='columns',ytitle='rows'
plot,[0],[0],yr=[cmin,cmax],xr=[0,numrows-1], $
	ytitle='detector columns',xtitle='detector row selects',/xstyle,/ystyle, psym=3,ticklen=1
for i=0,numcol-1 do begin
	pnt = where(pixel_flag(i,*) eq 0)
	pntfb = where(pixel_flag_fb(i,*) eq 0)
	if pnt(0) ne -1 then begin
		oplot, [pnt],[replicate(i,n_elements(pnt))], psym=2
	endif
	if pntfb(0) ne -1 then begin
		oplot, [pntfb],[replicate(i,n_elements(pntfb))], psym=4, symsize=1.5, color=1
	endif
endfor
xyouts, 6, 16, 'Stars have non-zero error aka. unlocked'
xyouts, 6, 13, 'Diamonds have fb=0 aka. turned off on purpose in pidz_dead_off.', color=1
device,/close

openw, 1, dotrun, /append
printf,1,'<LOCKTEST_FLAG>'
for i=0,numcol-1 do begin
    writeu,1,strcompress('<FLAGS_C'+string(i+coloffset)+'>',/remove_all)
    writeu,1,strcompress(string(transpose(pixel_flag(i,*))))
    printf,1,''
endfor
printf,1,'</LOCKTEST_FLAG>'
close,1

if file_search('/misc/mce_plots',/test_directory) eq '/misc/mce_plots' then begin
        if file_search('/misc/mce_plots/'+ctime,/test_directory) ne '/misc/mce_plots/'+ctime $
                then spawn, 'mkdir /misc/mce_plots/'+ctime
        spawn, 'cp -rf '+plot_name+' /misc/mce_plots/'+ctime
        spawn, 'cp -rf '+pixel_flag_name+' /misc/mce_plots/'+ctime
        spawn, 'chgrp -R mceplots /misc/mce_plots/'+ctime
endif



if keyword_set(interactive) then spawn,'ggv '+plot_name+' &'

print,' '
print,'###########################################################################'
print,' '
print,'To view the the frame_test_plot curves check the file'
print,string(plot_name)
print,' '
print,'###########################################################################'

;stop
fine:

end
