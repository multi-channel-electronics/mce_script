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
if count eq 32 then return,data
if count+start gt 32 then begin
    print,'EXTRACT_BITFIELD: count + start > 32!  Adjusting count...'
    count = 32-start
endif

; We can now assume that count < 32 and count+start <= 32

mask = ishft(1L,count)-1
data_out = ishft(long(data), -start) AND MASK

if not keyword_set(unsigned) then begin
    sign_bit = ishft(1L, count-1)
    extension_bits = ishft( ishft(1L, 32-count) - 1, count )
    neg = where(data_out AND sign_bit)
    if neg[0] ne -1 then $
      data_out[neg] = data_out[neg] OR extension_bits
endif

return,data_out

end
