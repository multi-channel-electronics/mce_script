; Function to compute rt(PSD) with the capability to bin
;the time stream prior to transforming (var. timebin),
;as well as to bin frequencies in logarithmic steps
; to facilitate plotting and fitting of data.
;
; Inputs:
;vec = data vector, preferably with 2^n*timebin points
;rate = rate in Hz at which vec was sampled
; timebin = number of bins to separate the time stream into
;for low frequency fft averaging
;freqstep = number of different frequency ranges over which
;to bin data by freqbin^(0 through freqstep - 1)
;freqbin^(0 through freqstep - 1) = number of different
;frequencies to bin together in each frequency step.
;
; Note: If freqstep is not set or = 0 frequency spacing is linear
;in returned value, and freqbin has no effect.
;    Also, default value for freqbin = 2.
;If freqbin < 2, then neither freqbin or freqstep have any effect.

; PSPEC_TOTAL function is at the bottom to facilitate compiling.

;--------------------------------------------------------------------------

;---------------------------------------------------------------------------

; Function to compute the square root of the power spectrum of a
; vector of
; data. The result returned is a vector. The units of the Y axis are
; in input value/rt(Hz).

; NOTE: To convert into actual input value/rt(Hz), simply divide
; output
;by freq(1)^0.5, where freq(1) is the smallest non-zero frequency
;component of the FFT.                   MDN July 12, 2006
;
; Input
;     vec     the vector to find the FFT of. Can be any length.
;Prior to using this function, subtract the DC level
;and slope of vec.
;
; Output:
;    fftvec    the sq rt of the PSD for 0 to Ny/2
;
; If the sample interval, the frequency is given by 1/(nfft*si)
; where nfft is the number of points to be sampled.
;
; This routine always uses the Welch apodization.
;
; As a first crack, don't do any overlapping.
;
; Original LP Jan 19, 1998
; Tests:
; Put in a sine wave and got back 0.707
; Tested with white noise

; Fix Window MDN July 12, 2006
; Window previously only dropped from 1 to ~0.94
; because of missing parentheses.

;-------------------------------------------------------------------------
FUNCTION PSPEC, vec
;
; Get size of input vector
;
isize = n_elements(vec)
;
; Window the data
;
window = FLTARR(isize)
window = 1. - ((FINDGEN(isize) - FLOAT(isize)/2.)/(FLOAT(isize)/2.))^2
winvec = window*vec
;set_plot, 'win'
;!p.multi = [0,1,2]
;plot, winvec
;plot, window
;stop
;winvec = vec
wss = float(isize)*TOTAL(window^2)
;wss = 1.
;
; This is a complex vector
;
fftvec = FFT(winvec, -1)
fftvec = ABS(fftvec)
fftvec = 2.*fftvec^2/wss
fftvec(0) = fftvec(0)/2.
fftvec = fftvec(0 : isize/2 - 1)
fftvec = SQRT(fftvec)*float(isize)
;
RETURN, fftvec
;
END

function pspec_total, vec, rate, timebin=timebin, freqstep=freqstep, freqbin=freqbin

if keyword_set(timebin) then timebin=timebin $
  else timebin=1
if keyword_set(freqstep) then freqstep=freqstep $
  else freqstep=0
if keyword_set(freqbin) then freqbin=freqbin $
  else freqbin=2

isize = n_elements(vec)
nfftpts = 4.*timebin
while nfftpts lt isize do begin
    nfftpts = nfftpts*2.
endwhile
if nfftpts ne isize then begin
    nfftpts = nfftpts/2.
    print, 'Using ', nfftpts, ' points for all ffts,  or ', nfftpts/timebin, ' points per fft.'
    print, 'Input vector has ', isize, ' points.'
    print, 'Having 2^n * timebin points optimizes fft calculation.'
endif
npts = nfftpts
print, 'Total length of time stream used is ', npts/rate, ' seconds'
;timebin = 4
nstp = npts/timebin
freqt = findgen(nstp/2)*rate/nstp
sumxft = fltarr(nstp/2)
for i=0,timebin-1 do begin
    xft = pspec(vec(i*nstp:(i+1)*nstp-1))
    sumxft = xft^2/freqt(1) + sumxft
endfor
sumxft = sumxft/timebin

;freqstep = 4
;freqbin = 3
if freqstep gt 0 then begin
    print, 'Binning high frequencies.'
    maxfreq = max(freqt)
    minfreq = freqt(1)
    freqexp = exp(alog(maxfreq/minfreq)/freqstep)
;print, minfreq, maxfreq, freqexp
    tot_pnts = 0
    for i=1,freqstep do begin
        curfreq = where(freqt lt minfreq*freqexp^i and freqt ge minfreq*freqexp^(i-1))
        tot_pnts = tot_pnts+floor(n_elements(curfreq)/freqbin^i)+1
    endfor
    data_out = fltarr(tot_pnts,2)
    ind_cnt = 0
    for i=1,freqstep do begin
        curfreq = where(freqt lt minfreq*freqexp^i and freqt ge minfreq*freqexp^(i-1))
        hmm = floor(n_elements(curfreq)/freqbin^i)+1
        highpnt = long(max(curfreq))
        lowpnt = long(highpnt - hmm*freqbin^i)
        freqtb = fltarr(hmm)
        outtb = fltarr(hmm)
        indpnt = lindgen(hmm)
        for j=0,freqbin^i-1 do begin
            freqtb = freqt(indpnt*freqbin^i+lowpnt+j)/freqbin^i + freqtb
            outtb = sumxft(indpnt*freqbin^i+lowpnt+j)/freqbin^i + outtb
        endfor
                                ; Approach above could be problematic
                                ; for lowest frequency data.

        data_out(ind_cnt:ind_cnt+hmm-1,0) = freqtb
        data_out(ind_cnt:ind_cnt+hmm-1,1) = outtb
        ind_cnt = ind_cnt + hmm
                                ;print, min(freqtb),max(freqtb), hmm
        ;oplot, freqtb, outtb, color=2000
        ;stop
    endfor
    data_sort = sort(data_out(*,0))
    data_out(*,0) = data_out(data_sort,0)
    data_out(*,1) = (data_out(data_sort,1))^.5
endif else begin
    print, 'No frequency binning.'
    data_out = fltarr(nstp/2,2)
    data_out(*,0) = freqt
    data_out(*,1) = (sumxft)^.5
endelse

;stop
return, data_out
end

