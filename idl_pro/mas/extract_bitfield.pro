function extract_bitfield,data,start=start,count=count,unsigned=unsigned

; MFH - 2008/04/07
; From each long int in array 'data', extract a long int based on the
; 'count' bits starting at lsb 'start', numbered from 0.  The
; extracted number is sign extended using its most significant bit
; unless the 'unsigned' keyword is set.

; Defaults
if not keyword_set(start) then start = 0
if not keyword_set(count) then count = 32 - start

; Handle common trivial cases
if count eq 32 then return,long(data)
if count+start gt 32 then begin
    print,'EXTRACT_BITFIELD: count + start > 32!  Adjusting count...'
    count = 32-start
endif

; We can now assume that count < 32 and count+start <= 32

if keyword_set(unsigned) then $
   data_out = ishft(ishft(data, 32-count-start), count-32) $
else $
   data_out = ishft(data, 32-count-start) / 2L^(32-count)

return, data_out

end
