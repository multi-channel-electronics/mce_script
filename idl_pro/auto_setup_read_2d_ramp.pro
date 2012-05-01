function auto_setup_read_2d_ramp, file_name, numrows=numrows

if not keyword_set(numrows) then numrows = 33

line=''
block=lonarr(8,numrows)
blockrow=lonarr(8)
roc=''
openr,1,file_name+'.run'
point_lun,1,0
repeat readf,1,roc until strmid(roc,0,6) eq "  <RC>"
close,1

openr,1,file_name+'.run'
point_lun,1,0

;while not eof(1) do begin

;read in lines until the line containing "start_data:"
repeat readf,1,line until strmid(line,0,10) eq "<par_ramp>"

;read the header
name=''
par=''
first=''
second=''

readf,1,par
;print, par ;TEST
pararr=strsplit(par,/extract)
readf,1,first
readf,1,first
firstarr=strsplit(first,/extract)
first=(firstarr(3))
;print, first ;TEST
readf,1,name
namearr=strsplit(name,/extract)
start_1st=fix(namearr(3))
step_1st=fix(namearr(4))
n_1st=fix(namearr(5))
;print, n_1st;TEST
;readf,1,start_1st,name
;print, start_1st ;TEST
;readf,1,step_1st,name
;print, step_1st ;TEST
if n_elements(pararr) gt 2 then begin
	readf,1,second
	readf,1,second
	readf,1,second
	readf,1,second
	secondarr=strsplit(second,/extract)
	second=(secondarr(3))
	;print, second ;TEST
	readf,1,name
	namearr=strsplit(name,/extract)
	start_2nd=fix(namearr(3))
	step_2nd=fix(namearr(4))
	n_2nd=fix(namearr(5))
endif else begin
	second=(firstarr(3))
        start_2nd=fix(namearr(3))
        step_2nd=fix(namearr(4))
        n_2nd=fix(namearr(5))
	n_1st=1
endelse
;print, n_2nd ;TEST
;readf,1,start_2nd,name
;print, start_2nd ;TEST
;readf,1,step_2nd,name
;print, step_2nd  ;TEST

;lable_array = strarr(3)
label_array = [roc,first,second]
;print, label_array ;TEST

spec_array = long([n_1st,start_1st,step_1st,n_2nd,start_2nd,step_2nd])

;read all the data
data_array=lonarr(n_1st,n_2nd,8,numrows)
close,1

header=lonarr(43)
checksum=lonarr(1)
openr,1,file_name
for m=0,n_1st-1 do begin
	for n=0,n_2nd-1 do begin
		readu,1,header		;header-discard for now
		for i=0,numrows-1 do begin
			readu,1,blockrow
			data_array(m,n,*,i)=blockrow
		endfor
		readu,1,checksum       ; checksum--discard
;stop
	endfor
endfor

close,1
return,{labels:label_array,specs:spec_array,data:data_array}

end
