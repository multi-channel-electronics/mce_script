pro auto_iv_and_squids,skip_squids=skip_squids,acquire_n_pts=acquire_n_pts

tes_end_bias = 9000
shuntfile = '/data/SRDP/tes.x.3-3f/johnson_res.dat'
time=string(systime(1,/utc),format='(i10)')
close,/all
spawn,'exitalltasks'
spawn,'killtasks'
spawn,'startdas_text mce'
spawn,'set_directory'

current_data = ''
openr, 3, '/data/cryo/current_data_name'
readf, 3, current_data

config_file = 'config_mce_auto_setup_'+current_data

if not keyword_set(skip_squids) then begin
	squid_dir = time+'.squids'	
	spawn, 'mkdir /data/cryo/'+current_data+'/'+squid_dir
	spawn, 'mkdir /data/cryo/'+current_data+'/analysis/'+squid_dir
	auto_setup_squids,squid_dir+'/auto_',/remote
	spawn, 'cp /data/cryo/'+current_data+'/'+config_file+' /data/cryo/'+current_data+'/'+squid_dir+'/'+config_file
endif

spawn,config_file
iv_dir = time+'.iv'
spawn, 'ramp_tes_bias '+iv_dir+' 1'
iv_anal_mce,/plotgen,filename='/data/cryo/'+current_data+'/'+iv_dir,jshuntfile=shuntfile
spawn, 'ggv /data/cryo/'+current_data+'/'+iv_dir+'.data/IV_plots.ps &'

spawn,'exitalltasks'
spawn,'killtasks'
spawn,'startdas_bin mce'
spawn,config_file
spawn,'w rc1 data_mode 2'
spawn,'w cc use_dv 2'
spawn,'w bc2 bias '+strtrim(string(tes_end_bias))

print,'------------------------------------------------------------------------------------- '
print,'------------------------------------------------------------------------------------- '
print,'SQUIDs are tuned.  I-V was acquired.  TESs were biased normal, then set to bias = '+strtrim(string(tes_end_bias))
print,'Data acquisition currently set to sync box controlled filtered data in binary format.'
print,'BEFORE RUNNING CONFIG FILE AGAIN, CHECK THE DATA_MODE AND USE_DV VARIABLES IN THE CONFIG FILE:'
print,'/data/cryo/'+current_data+'/'+config_file

if keyword_set(acquire_n_pts) then begin
    spawn, 'mceframetest 1 '+strtrim(string(acquire_n_pts))+' 1 '+time+'.frames rc1' 
endif else begin
    print,'To acquire data, use mceframetest at shell prompt'
endelse

print,'Data acquisition currently set to sync box controlled filtered data in binary format.'
print,'BEFORE RUNNING CONFIG FILE AGAIN, CHECK THE DATA_MODE AND USE_DV VARIABLES IN THE CONFIG FILE:'
print,'/data/cryo/'+current_data+'/'+config_file

end
