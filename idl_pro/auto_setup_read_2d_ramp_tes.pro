function auto_setup_read_2d_ramp_tes, file_name

openr,1,file_name
line=''
repeat readf,1,line until strmid(line,4,9) eq "data_mode"
data_mode=string(line)
repeat readf,1,line until strmid(line,0,10) eq "end_status"

point_lun,1,0

;while not eof(1) do begin

;read in lines until the line containing "start_data:"
	repeat readf,1,line until strmid(line,0,11) eq "start data:"

;read the header
	name=''
	card=''
	first=''
	second=''

	readf,1,card
print, card ;TEST
	readf,1,first
print, first ;TEST
	readf,1,n_1st,name
print, n_1st;TEST
	readf,1,start_1st,name
print, start_1st ;TEST
	readf,1,step_1st,name
print, step_1st ;TEST
	readf,1,second
print, second ;TEST
        readf,1,n_2nd,name
print, n_2nd ;TEST
        readf,1,start_2nd,name
print, start_2nd ;TEST
        readf,1,step_2nd,name
print, step_2nd  ;TEST

block=reform(lonarr(8,41,fix(n_1st)))


;	lable_array = strarr(3)
	label_array = [card,first,second]
print, label_array ;TEST

	spec_array = [n_1st,start_1st,step_1st,n_2nd,start_2nd,step_2nd]

;read all the data
	data_array=lonarr(n_1st,n_2nd,8,41)
;stop
	;for m=0,n_1st-1 do begin
	for n=0,n_2nd-1 do begin
		readf,1,line		;header--discard for now
		readf,1,block
		data_array(*,n,*,*)=block
		readf,1,checksum       ; checksum--discard
          
;         print, m,n,checksum  ;TEST

	endfor
	;endfor

;endwhile

close,1
return,{labels:label_array,specs:spec_array,data:data_array}

end
