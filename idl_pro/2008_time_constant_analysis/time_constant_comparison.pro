pro time_constant_comparison

path='/mnt/act2/mce_mbac/AR1/20081212/'

restore, path+'results_all_data/tau_fits.sav'
tau_all = tau_fits
restore, path+'results_half1_data/tau_fits.sav'
tau_h1 = tau_fits
restore, path+'results_half2_data/tau_fits.sav'
tau_h2 = tau_fits

set_plot, 'ps'
device, filename=path+'time_constant_comparison.ps'
!p.charsize=1.5

plot,[0,200],[0,200],xr=[0,200],yr=[0,200],xtitle='Time constants first half of data (Hz)', ytitle='Time constants second half of data (Hz)'
for i=0,31 do oplot, tau_h1(1,*,0,i), tau_h2(1,*,0,i), psym=2, symsize=0.3

;stop

plot,[0,200],[0,200],xr=[0,200],yr=[0,200],xtitle='Time constants all of data (Hz)', ytitle='Time constants first half of data (Hz)'
for i=0,31 do oplot, tau_all(1,*,0,i), tau_h1(1,*,0,i), psym=2, symsize=0.3

;stop

plot,[0,200],[0,200],xr=[0,200],yr=[0,200],xtitle='Time constants all of data (Hz)', ytitle='Time constants second half of data (Hz)'
for i=0,31 do oplot, tau_all(1,*,0,i), tau_h2(1,*,0,i), psym=2, symsize=0.3

device,/close

stop

end
