function auto_setup_read_2d_ramp_s1, file_name

numrows=33

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
repeat readf,1,line until strmid(line,0,10) eq "<par_ramp>"

;read the header
name=''
par=''
first=''
second=''

readf,1,par
;print, par ;TEST
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
;readf,1,second
;secondarr=strsplit(second,/extract)
;second=(secondarr(2))
;print, second ;TEST
;readf,1,name
;namearr=strsplit(name,/extract)
start_2nd=0;fix(namearr(n_elements(namearr)-3))
step_2nd=1;fix(namearr(n_elements(namearr)-2))
n_2nd=1;fix(namearr(n_elements(namearr)-1))

block=reform(lonarr(8,33,fix(n_1st)))
;blockrow=reform(lonarr(8,fix(n_1st)))

;lable_array = strarr(3)
label_array = [roc,first]
;print, label_array ;TEST

spec_array = [n_1st,start_1st,step_1st,n_2nd,start_2nd,step_2nd]

;read all the data
data_array=lonarr(n_1st,n_2nd,8,numrows)

;	;for m=0,n_1st-1 do begin
;	for n=0,n_2nd-1 do begin
;		readf,1,line		;header--discard for now
;		readf,1,block
;		data_array(*,n,*,*)=block
;		readf,1,checksum       ; checksum--discard
          
;         print, m,n,checksum  ;TEST

;	endfor
;	;endfor

;endwhile

close,1
;return,{labels:label_array,specs:spec_array,data:data_array}

header=lonarr(43)
checksum=lonarr(1)
openr,1,file_name
for m=0,n_1st-1 do begin
        for n=0,n_2nd-1 do begin
                readu,1,header          ;header-discard for now
                for i=0,numrows-1 do begin
                        readu,1,blockrow
                        data_array(m,n,*,i)=blockrow
;stop
                endfor
                readu,1,checksum       ; checksum--discard
;stop
        endfor
endfor

close,1
return,{labels:label_array,specs:spec_array,data:data_array}



end
