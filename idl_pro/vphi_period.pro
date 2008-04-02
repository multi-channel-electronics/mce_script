; vphi_period.pro
; 
; Determine the period of a periodic waveform.
;  - uses the right side of the curve, either half of the graph or
;    fit_width samples.
;  - iteratively determines the first non-trivial 'zero' in the
;    shifted chi-square, F(a) = integral( [f(x+a) - f(x)]^2 )
; If your graph has at _least_ two full periods, you can just call
; vphi_period(y).  If it is less than two full periods, set fit_width
; to the size of the right-hand region for which you want to find
; repetition.

function vphi_period, y, fit_width=fit_width

if keyword_set(fit_width) then $
  start_point = n_elements(y) - fit_width $
else $
  start_point = n_elements(y) / 2
width = n_elements(y) - start_point
margin = n_elements(y) - width
right_half = y(start_point:*)

c = fltarr(margin)
for a=0,margin-1 do begin
    c(a) = total( (y( start_point-a + indgen(width) ) - right_half)^2 )
endfor

; Normalize so that segment cannot match a flat segment at the same level
c = c / total((right_half - mean(right_half))^2)

; Make a comb, increase threshold until teeth are narrow compared to
; spacing.

thresh = 0.5
done = 0
while not done do begin
    comb = intarr(margin)
    comb(where(c lt thresh)) = 1
    
; For this comb to work we need:
;     ^_^_ at least
    n_comb = n_elements(comb)
    dcomb = comb(1:*) - comb(0:(n_comb-2))
    
    dns = where(dcomb lt 0)
    ups = where(dcomb gt 0)
    
    if n_elements(dns) lt 2 then begin
        print, 'Curve is not obviously periodic.'
        return,-1
    endif

    if ups(0) le dns(0) then begin
        print, 'Curve is messed up somehow.'
        return,-1
    endif
    
    gap = float(ups(0)-dns(0))
    wid = float(dns(1)-ups(0))
;    print, 'thresh=',thresh, '  Gap=',gap, '   Width=',wid
;    plot, comb
    if wid/gap lt 0.1 then done = 1
    thresh = thresh * 0.7
    done = 1
endwhile

; Find best match in first region
match = where (c eq min(c(ups(0):dns(1))))
return, match

end
