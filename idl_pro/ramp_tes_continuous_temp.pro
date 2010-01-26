pro ramp_tes_continuous_temp, COLUMN=column, ROW=row,RC=rc,directory,interactive=interactive,acquire=acquire,npts=npts,ptcut=ptcut,ivdetect=ivdetect,autoscale=autoscale,yrange=yrange,winy=winy,temp_start=temp_start,temp_end=temp_end,txt=txt,tempfile=tempfile

;JAB 20081002 edited ramp_tes_continuous.pro for use in the 4-tile
;array utilizing mas_data.pro. 

;NOTE:  quick kludge. Use rc=0 instead of rc=s

;If tempfile, the temperature file from HK data converted to proper
;format (FPU Cu, Time&Date,time,elapsed), then keep it in "directory".
;Tempfile is a keyword telling idl to look for that .txt file in the
;directory. 

close,/all

starttime=systime(1)
if keyword_set(npts) then npts=npts else npts=1000;1435406 ;npts=number of data points, 1 point = 0.0025s
if (rc eq 1) or (rc eq 2) then numcol=8
if rc eq 0 then numcol=16

; feeding fb1 and tesbias total line impedances
if rc eq 1 then begin
rfb1=[2321.15,2319.08,2318.11,2317.99,2378.86,2378.99,2320.63,2322.96]  ;ref 'tbias_fb1_resist_calc_20080920_run1.1.xls' 
rtes=[669.22,671.20,668.20,667.79,668.77,674.54,673.47,675.42]
endif
if rc eq 2 then begin
rfb1=[2273.35,2270.30,2269.60,2269.36,2271.18,2271.79,2272.03,2273.22]
rtes=[0.0,0.0,624.10,624.56,624.02,626.15,625.70,626.19]
endif
if rc eq 0 then begin
rfb1=[2321.15,2319.08,2318.11,2317.99,2378.86,2378.99,2320.63,2322.96,2273.35,2270.30,2269.60,2269.36,2271.18,2271.79,2272.03,2273.22]
rtes=[669.22,671.20,668.20,667.79,668.77,674.54,673.47,675.42,0.0,625.0,624.10,624.56,624.02,626.15,625.70,626.19]
endif

tileinfo=['1: T090112.2','2: JAB090105.1 ','3: T090112.1','4: JAB081002.2']      ;tile fab SNs

; feeding maximum output voltage (Vfsd)

if rc eq 1 then vfb1=[.9400,.9472,.9423,.9455,.9446,.9477,.9438,.9479]
if rc eq 2 then vfb1=[.9503,.9505,.9454,.9509,.9446,.9462,.9438,.9424]
if rc eq 0 then vfb1=[.9400,.9472,.9423,.9455,.9446,.9477,.9438,.9479,.9503,.9505,.9454,.9509,.9446,.9462,.9438,.9424]

rsh=.0034                                                ;might be lower at 250mK still need to determine
m_infb1=15.9                                            ;best guess at the moment

filter_gain=1216.                                        ;filter gain on filtered data (e.g. data_mode = 2 or 10)

vtbias=2.500        ;very uniform across columns

ctime=1111111111;string(file_name,format='(i10)')

rcdatamode=rc
if keyword_set(acquire) then begin
	auto_setup_command,'rc'+strcompress(string(rcdatamode),/REMOVE_ALL)+' data_mode '+data_mode
	spawn,'ramp_tes_continous '+file_name+' '+strcompress(string(RC),/REMOVE_ALL)
endif

directory='/data/cryo/'+directory
ftemp=file_search(directory+'/*.*')
files=file_search(directory+'/*12*')
numdatpt=(n_elements(files)-2)
dotrun=file_search(directory+'/*.run')
dotbias=file_search(directory+'/*.bias')
dottxt=file_search(directory+'/*.txt')
ctimeindex=lonarr(1,numdatpt)
ctimestart=strmid(files[0],14,10,/reverse_offset)


save_dir=directory+'/analysis/'
spawn, 'mkdir '+save_dir+'

col_name =''
row_name = ''
line=''

if rc eq 1 then data_mode_str='<RB rc1 data_mode>'
if rc eq 2 then data_mode_str='<RB rc2 data_mode>'
if rc eq 0 then data_mode_str='<RB rc1 data_mode>'

openr, 1, dotrun
repeat readf,1,line until strmid(line,0,18) eq data_mode_str 
data_mode=fix(strmid(line,19,8))
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

; reading in applied tesbias ramp information
tes_bias=fltarr(1000)
b=0.0
openr, 1, dotbias
bias_count=0
while (not eof(1)) do begin
readf,1,b
tes_bias(bias_count)=b
bias_count=bias_count+1
endwhile
tes_bias=tes_bias(0:bias_count-1)

resarr=dblarr(numcol,numrows,numdatpt)
minfbarr=dblarr(numcol,numrows,numdatpt)

tes_bias=tes_bias*(vtbias/2.^16)


temp_xdata=fltarr(numdatpt)
if keyword_set(tempfile) then begin
   temp_data=read_ascii(data_start=3,delimiter=' ',dottxt)
   fpu_data=temp_data.field1(0,*)
   temp_data_pts=n_elements(temp_data.field1(5,*))
   elapsed_data=dblarr(temp_data_pts)
   for i=0,(temp_data_pts-1) do elapsed_data[i]=temp_data.field1(5,i)
   ctime_data=elapsed_data+ctimestart 
endif else begin
if temp_end gt temp_start then temp_xdata=findgen(numdatpt)*((temp_end-temp_start)/(numdatpt-1))+replicate(temp_start,numdatpt)
if temp_start gt temp_end then temp_xdata=(findgen(numdatpt)*((temp_start-temp_end)/(numdatpt-1))+replicate(temp_end,numdatpt))
endelse


if keyword_set(ptcut) then begin
   ff_i=2                           ;make this 2, provided first two files are .run and .bias
   ff_f=3323
endif else begin
   ff_i=2       ;make this 2, provided first two files are .run and .bias
   ff_f=(numdatpt+1)
endelse

for ff=ff_i,ff_f,1 do begin
	file_name=files[ff]
	ctimestamp=strmid(file_name,9,10,/reverse_offset)
	datpt=ff-2
	ctimeindex[datpt]=ctimestamp
        if keyword_set(tempfile) then temp_xdata[datpt]=spline(ctime_data,fpu_data,ctimestamp)  
     
pixel_flag=intarr(numcol,numrows)
pixel_flag(*,*)=1
pixel_flag_fb=intarr(numcol,numrows)
pixel_flag_fb(*,*)=1

!p.multi=[0,4,2]

if n_elements(column) eq 0 then begin
  cmin=0
  cmax=numcol-1
endif else begin
  cmin=column
  cmax=column
  !p.multi=[0,1,2] 
  col_name = 'c'+ string(column, format='(i1)')
endelse

if n_elements(row) eq 0 then begin
  rmin=0
  rmax=numrows-1
endif else begin
  rmin=row
  rmax=row
  !p.multi=[0,1,2]
  row_name =  strcompress('r'+ string(row),/REMOVE_ALL)
endelse

;;pixel_flag_name=plot_name+'_pixel_flag.ps'
;;plot_name = plot_name+'_' + col_name + row_name + '.ps'

;;print, plot_name

line=''

set_plot,'x'

m=0


npts = m   ; set npts to actual number of  frames read.

;;; NEW CODE BREAK

;; starting new code here leaving above alone for reference
; ';' = just recently edited out ';;' means commented out before
;feed tes_bias & fb_corr

fb=mas_data(file_name,/no_runfile,data_mode=data_mode)


;the looping over rows and columns begins below... leave this
;part. Above needs revision for use with mas_data.pro

!p.multi=[0,1,2]

for n=0,numcol-1 do begin
fb[n,*,*]=fb[n,*,*]*vfb1[n]
endfor
fb_corr=fb/(2.^14)


if (data_mode eq 10) or (data_mode eq 2) then fb_corr=fb_corr/filter_gain
	
for n_row = rmin, rmax  do begin
  	for n_col = cmin, cmax do begin

           der=deriv(tes_bias,fb_corr[n_col,n_row,*])
	
		if keyword_set(interactive) then begin
			plot, tes_bias, der, /ynozero,thick=4,title='fb_derivative',xtitle='TES BIAS (V)'	
			
			if keyword_set(winy) then begin
				plot, tes_bias, fb_corr[n_col, n_row,*], /ynozero,title='FB1 COL='+string(n_col)+'ROW='+string(n_row),xtitle='TES BIAS(V)',ytitle='FB1 (V)',psym=1,yrange=winy
				endif else begin
				plot, tes_bias,fb_corr[n_col,n_row,*],/ynozero,title='FB1 COL='+string(n_col)+'ROW='+string(n_row),xtitle='TES BIAS (V)',ytitle='FB1 (V)',psym=1 
			endelse
		endif
		
		;setting up to parse data into blocks at fb and daq jumps
		
		rtesnorm=replicate(!values.f_nan,1,100)
		m_infb=replicate(!values.f_nan,1,100)	

		mask=abs(der - mean(der)) gt (4*stddev(der))
		mask_i=where(mask eq 1)
		
		if (mask_i[0] eq -1) then begin
			mask_i=0
			nmask=0
		endif else nmask=n_elements(mask_i)

		buffer=3
		ii=0
		jj=0		;initialize the start of a new block
		limeof=(n_elements(tes_bias)-1)
	
	if (nmask ne 0) then begin									;if true then parse data in blocks at jumps
			flag=intarr(1,nmask)
			if (mask_i[ii] eq 0) then begin
				if (nmask gt 1) then begin
					for xx=ii,(nmask-2),1 do flag[xx]=mask_i[xx+1]-mask_i[xx]			
					xx=ii
					while (flag[xx] eq 1) do xx=xx+1
					ii=xx

					if (ii lt (nmask-1)) then lim=(mask_i[ii+1]-buffer) else lim=limeof
				endif else lim=limeof
			jj=mask_i[ii]+buffer
			endif else lim=(mask_i[ii]-buffer)
		
		while (ii le nmask) do begin

			if (jj lt lim) then begin
					
				tes_bias_block=tes_bias[jj:lim]
				fb_corr_block=fb_corr[n_col,n_row,jj:lim]
;				fitblock=linfit(tes_bias_block,fb_corr_block)		
				fitblock=ladfit(tes_bias_block,fb_corr_block)
				yfit=fitblock[0]+fitblock[1]*tes_bias_block			
	
				n_maskpts=1
				while (n_maskpts gt 0) do begin
					resid=yfit-fb_corr_block
					maskpts=where(abs(resid) gt 2*stddev(resid))
					if (maskpts[0] eq -1) then n_maskpts=0 else n_maskpts=n_elements(maskpts)
					if (n_maskpts ne 0) then for j=0,(n_maskpts-1),1 do fb_corr_block[maskpts[j]]=!values.f_nan
				
					non_nan=where(finite(fb_corr_block) ne 0)				;fitting routines, unlike plot, choke on NaN
					fitblock=ladfit(tes_bias_block[non_nan],fb_corr_block[non_nan],ABSDEV=absdev)
					yfit=fitblock[0]+fitblock[1]*tes_bias_block
				endwhile
				
				if keyword_set(interactive) then oplot,tes_bias_block,fb_corr_block,color='00FF00'x	;plot good points that made cut in GREEN
				if(absdev gt 1) then begin
					rtesnorm[ii]=!values.f_nan
					m_infb[ii]=!values.f_nan
				endif else begin
					rtesnorm[ii]=abs(rsh*((m_infb1*(rfb1[n_col]/rtes[n_col])*(1/abs(fitblock[1])))-1))
					m_infb[ii]=abs(fitblock[1]*(rtes[n_col]/rfb1[n_col]))
					if keyword_set(interactive) then begin
						oplot,tes_bias_block,yfit,color='0000FF'x	;plot final corrected fit line in RED	
					endif
				endelse
			endif		
					
			ii=ii+1

			if (ii lt nmask) then begin
				if (mask_i[ii] eq (mask_i[ii-1]+1)) then begin
					jj=mask_i[ii]+buffer
					if (ii eq (nmask-1)) then lim=limeof else lim=(mask_i[ii+1]-buffer)
				endif else begin
					jj=mask_i[ii-1]+buffer
					lim=(mask_i[ii]-buffer)
				endelse
			endif else begin
				if (ii le nmask) then begin
					jj=mask_i[ii-1]+buffer
					lim=limeof
				endif
			endelse
		
;			if (ii lt (nmask-1)) then begin
;				while (mask_i[ii] eq (mask_i[ii+1]-1)) do ii=ii+1
;			endif			

		endwhile	
	

	rtesnorm_mean=mean(rtesnorm[0:(ii-2)],/nan)
	m_infb_mean=mean(m_infb[0:(ii-2)],/nan)	
	
	resarr[n_col,n_row,datpt]=rtesnorm_mean
	minfbarr[n_col,n_row,datpt]=m_infb_mean

	endif else begin			; calculations when there are no DAC/fb jump blocks
;               fit=linfit(tes_bias,fb_corr[n_col,n_row,*])
                fit=ladfit(tes_bias,fb_corr[n_col,n_row,*])
		yfit=fit[0]+fit[1]*tes_bias
	
		n_maskpts=1
		while (n_maskpts gt 0) do begin
			resid=yfit-fb_corr[n_col,n_row,*]
			maskpts=where(abs(resid) gt 1*stddev(resid))
			if (maskpts[0] eq -1) then n_maskpts=0 else n_maskpts=n_elements(maskpts)
			if (n_maskpts ne 0) then for j=0,(n_maskpts-1),1 do fb_corr[n_col,n_row,maskpts[j]]=!values.f_nan

			non_nan=where(finite(fb_corr[n_col,n_row,*]) ne 0)				;fitting routines, unlike plot, choke on NaN
			fit_corr=ladfit(tes_bias[non_nan],fb_corr[n_col,n_row,non_nan])
			yfit=fit_corr[0]+fit_corr[1]*tes_bias
		endwhile

		if keyword_set(interactive) then begin
		oplot,tes_bias,fb_corr[n_col,n_row,*],color='00FF00'x		;plot the data actually used in fit in GREEN
		oplot,tes_bias,yfit,color='0000FF'x				;plot the final corrected fit line in RED
		endif
	
		non_nan=where(finite(fb_corr[n_col,n_row,*]) ne 0)				;fitting routines, unlike plot, choke on NaN
		fit_corr=ladfit(tes_bias[non_nan],fb_corr[n_col,n_row,non_nan],ABSDEV=absdev)

		if (absdev gt 1) then begin
			rtesnorm_fit=!values.f_nan
			m_infb_fit=!values.f_nan
		endif else begin
			rtesnorm_fit=abs(rsh*((m_infb1*(rfb1[n_col]/rtes[n_col])*(1/abs(fit_corr[1])))-1))
			m_infb_fit=abs(fit_corr[1]*(rtes[n_col]/rfb1[n_col]))
			if keyword_set(interactive) then oplot,tes_bias,yfit,color='0000FF'x				;plot the final corrected fit line in RED	
		endelse

	resarr[n_col,n_row,datpt]=rtesnorm_fit
	minfbarr[n_col,n_row,datpt]=m_infb_fit	
	
	endelse


;		xyouts, 0.0*(!D.X_SIZE), 1.00*(!D.Y_SIZE), data_mode, /device

if keyword_set(interactive) then begin
	print,'ctime of file is= '+strcompress(string(ctimestamp),/remove_all)
	print,'resistance fit is= '+strcompress(string(resarr[n_col,n_row,datpt]),/remove_all)
        print,'turns ratio fit is= '+strcompress(string(minfbarr[n_col,n_row,datpt]),/remove_all)
	pause
endif

   	endfor               	; end column loop
endfor    			; end row loop    

endfor				; end data point loop

tc_arr=fltarr(16,33)            ; include DS, but don't show in output file
rnorm_arr=fltarr(16,33)


save_file=save_dir+'RvsT_all'
set_plot,'ps'
device,/landscape,xsize=25.,ysize=17.
device,filename=save_file+'.ps'

for n_col=cmin,cmax do begin	; loop over col's and rows for analysis files
for n_row=rmin,rmax do begin

if (n_col lt 4) then tile=tileinfo[0]
if (n_col gt 3) and (n_col lt 8) then tile=tileinfo[1]
if (n_col gt 7) and (n_col lt 12) then tile=tileinfo[2]
if (n_col gt 11) then tile=tileinfo[3]

!p.multi=[0,1,1]
!p.charsize=1.0
!p.charthick=1.5
!p.thick=1.5

;save_file=save_dir+'RvsT_c'+strcompress(string(n_col),/remove_all)+'r'+strcompress(string(n_row),/remove_all)

;the statement block below is really inefficient.  should clean it
;later... it's written this way for the case of FPU temp ramp down.  

;Used to determine Tc

i=0
if keyword_set(tempfile) then begin
   if (temp_xdata[0] gt temp_xdata[ff_f-2]) then begin
      tc_flag=(reverse(minfbarr[n_col,n_row,*],3) lt 13.) 
      if tc_flag[0] eq 1 then tc_start=0.0 else begin        ;the case when all resistive
         repeat i=i+1 until (tc_flag[i]) eq 1 or (i eq ff_f-2)
         if i eq ff_f-2 then tc_start=0.0 else tc_start=temp_xdata[(ff_f-2)-i] ;the case when all supercond.
      endelse 
   endif else begin
         tc_flag=(minfbarr[n_col,n_row,*] lt 13.)
         if tc_flag[0] eq 1 then tc_start=0.0 else begin
            repeat i=i+1 until (tc_flag[i]) eq 1 or (i eq ff_f-2)
            if i eq ff_f-2 then tc_start=0.0 else tc_start=temp_xdata[i]
         endelse   
   endelse
endif else begin
   if (temp_start gt temp_end) then begin
      tc_flag=(reverse(minfbarr[n_col,n_row,*],3) lt 13.) 
      if tc_flag[0] eq 1 then tc_start=0.0 else begin
         repeat i=i+1 until (tc_flag[i]) eq 1 or (i eq ff_f-2)
         if i eq ff_f-2 then tc_start=0.0 else tc_start=temp_xdata[(ff_f-2)-i]
      endelse   
   endif else begin
         tc_flag=(minfbarr[n_col,n_row,*] lt 13.)
         if tc_flag[0] eq 1 then tc_start=0.0 else begin
            repeat i=i+1 until (tc_flag[i]) eq 1 or (i eq ff_f-2)
            if i eq ff_f-2 then tc_start=0.0 else tc_start=temp_xdata[i]
         endelse
      endelse
endelse
tc_arr[n_col,n_row]=tc_start

;code below is used to determine Rnorm... Rnorm only if transition
;detected... otherwise 0.000
rnorm=0.0
rnorm_flag=where(minfbarr[n_col,n_row,*] lt 13.)
if (rnorm_flag[0] ne -1) and (n_elements(rnorm_flag) gt 50) then begin

    if (temp_xdata[0] lt temp_xdata[n_elements(temp_xdata)-1]) then begin
        rn_mean=mean(resarr[n_col,n_row,rnorm_flag[50:(n_elements(rnorm_flag)-1)]])
        rn_stdv=stdev(resarr[n_col,n_row,rnorm_flag[50:(n_elements(rnorm_flag)-1)]])
    endif else begin
        rn_mean=mean(resarr[n_col,n_row,rnorm_flag[0:(n_elements(rnorm_flag)-50)]])
        rn_stdv=stdev(resarr[n_col,n_row,rnorm_flag[0:(n_elements(rnorm_flag)-50)]])
    endelse

rn_good=where(abs(resarr[n_col,n_row,*]-rn_mean) lt .5*rn_stdv)

if (rn_good[0] ne -1) and (tc_start gt 0)  then begin
;   rnorm_fit=ladfit(temp_xdata[rn_good],resarr[n_col,n_row,rn_good])
   rnorm=mean(resarr[n_col,n_row,rn_good])
   rnorm_arr[n_col,n_row]=rnorm
endif
endif

yrange_use=[0,.1]
if keyword_set(autoscale) then if (rnorm gt .1) then yrange_use=[0,(2*rnorm)]
if keyword_set(yrange) then yrange_use=[0,yrange]

if (tc_start gt 0) then begin
   tc_string='Tc = '+strcompress(string(tc_start,format='(f9.4)'),/remove_all)+'K'
   rn_string='Rn = '+strcompress(string(rnorm,format='(f9.4)'),/remove_all)+'!7X!X'
endif else begin
   tc_string='transition not detected'
   rn_string=' '
endelse

;set_plot,'ps'
;device,/landscape,xsize=25.,ysize=17.
;device,filename=save_file+'.ps'
plot,temp_xdata,resarr[n_col,n_row,0:datpt],psym=4,yrange=yrange_use,title='R vs. T (COL='+strcompress(string(n_col),/remove_all)+' ROW='+strcompress(string(n_row),/remove_all)+') TILE='+tile,xtitle='TEMPERATURE (K)',ytitle='RESISTANCE (Ohms)',/xstyle
if (tc_start gt 0) then begin 
   oplot,[tc_start,tc_start],[0,1],linestyle=2
   oplot,[temp_xdata[0],temp_xdata[n_elements(temp_xdata)-1]],[rnorm,rnorm],linestyle=3
;  oplot,temp_xdata,(rnorm_fit[0]+rnorm_fit[1]*temp_xdata),linestyle=3
   if (rn_good[0] ne -1) then oplot,temp_xdata[rn_good],resarr[n_col,n_row,rn_good],psym=1   ;added [0] to rn_good JAB 20090312
endif
xyouts,17000,15000,tc_string,/device,charsize=1.5
xyouts,17000,14000,rn_string,/device,charsize=1.5
xyouts,0,0,directory,charsize=.6,/device
erase
;device,/close

;spawn, 'ps2pdf '+save_file+'.ps'

set_plot,'x'
plot,temp_xdata,resarr[n_col,n_row,0:datpt],psym=4,yrange=yrange_use,title='R vs. T (COL='+strcompress(string(n_col),/remove_all)+' ROW='+strcompress(string(n_row),/remove_all)+') TITLE='+tile,xtitle='TEMPERATURE (K)',ytitle='RESISTANCE (Ohms)',/xstyle
if (tc_start gt 0) then begin 
   oplot,[tc_start,tc_start],[0,1],linestyle=2
;   oplot,temp_xdata,(rnorm_fit[0]+rnorm_fit[1]*temp_xdata),linestyle=3,color='0000ff'x
   oplot,[temp_xdata[0],temp_xdata[n_elements(temp_xdata)-1]],[rnorm,rnorm],linestyle=3,color='0000ff'x
   if (rn_good[0] ne -1) then oplot,temp_xdata[rn_good],resarr[n_col,n_row,rn_good],color='00ff00'x
   xyouts,400,350,tc_string,/device,charsize=1.5
   xyouts,400,330,rn_string,/device,charsize=1.5
endif else xyouts,400,400,'transition not detected',/device,charsize=1.5
xyouts,0,0,directory,charsize=.6,/device


;save, resarr[n_col,n_row,*],file=save_file+'.sav'
;resarr_filename='??'
;openw,1,'filepath _+_ filename'
;writeu,1,resarr_filename
;close,1,

if keyword_set(txt) then begin
data_file=save_file+'.txt'
openw,lun,data_file,/get_lun,/append
printf,lun,'COL='+strcompress(string(n_col),/remove_all)+' ROW='+strcompress(string(n_row),/remove_all),' tile=',tile
printf,lun,directory
printf,lun,'Tc='+strcompress(string(tc_start),/remove_all)+'  Rnorm='+strcompress(string(rnorm),/remove_all)
printf,lun,'  CTIME         ','TEMP (K)  ','M_infb ','RES (Ohms)'
for i=0,datpt do printf,lun,ctimeindex[i],temp_xdata[i],minfbarr[n_col,n_row,i],resarr[n_col,n_row,i],format='(i,f10.4,f10.4,e11.4)'
free_lun,lun
endif

set_plot,'ps'
endfor
endfor

device,/close

if keyword_set(txt) then begin
tc_file=save_dir+'Tc.txt'
rn_file=save_dir+'Rnorm.txt'
openw,lun,tc_file,/get_lun
printf,lun,'TES TRANSITION TEMPERATURES (K)'
printf,lun,directory
printf,lun,'  '
printf,lun,tc_arr,format='(16(f6.4,x))'
free_lun,lun
openw,lun,rn_file,/get_lun
printf,lun,'TES NORMAL RESISTANCE'+'(Ohms)'
printf,lun,rnorm_arr,format='(16(f6.4,x))'
free_lun,lun
endif


endtime=systime(1)
print,'run time is ',(endtime-starttime)

;n_maskpts=1
;while (n_maskpts gt 0) do begin
;	maskpts=where(abs(resarr[n_col,n_row,*]-mean(resarr[n_col,n_row,*],/nan)) gt 2*stddev(resarr[n_col,n_row,*],/nan))
;	if (maskpts[0] eq -1) then n_maskpts=0 else n_maskpts=n_elements(maskpts)
;	if (n_maskpts ne 0) then for j=0,(n_maskpts-1),1 do resarr[n_col,n_row,maskpts[j]]=!values.f_nan
;	plot,resarr[n_col,n_row,*]
;endwhile
;
end

