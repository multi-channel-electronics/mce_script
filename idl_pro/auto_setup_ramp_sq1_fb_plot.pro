pro auto_setup_ramp_sq1_fb_plot, file_name,RC=rc,interactive=interactive,numrows=numrows,rows=rows, $
                                 acq_id=acq_id,quiet=quiet,poster=poster,extra_labels=extra_labels


;  Aug. 21, 2006 created by Elia Battistelli (EB) for the auto_setup program
;	   adapted from ramp_sq1_fb_plot.pro 
;  Feb. 18, 2007 M. Niemack added new_adc_offset calculation method 
;		to find largest region with non-zero slope

common ramp_sq1_var

;Init
if not keyword_set(acq_id) then acq_id = 0

;Close all open files. It helps avoid some errors although shouldn't be necessary:
close,/all

;Communication:
if not keyword_set(quiet) then begin
    print,''
    print,'###########################################################################'
    print,'#5) The fifth step is to check whether the locking is succesfull. We then #'
    print,'#   run a ramp_SQ1_fb and we check the SQ1 V-phi curves.                  #'
    print,'###########################################################################'
    print,''
endif

default_folder = '/data/cryo/'
default_date = 'current_data/'
date= default_date
folder= default_folder

paths = strsplit(file_name,'/',/extract)
ctime=paths[n_elements(paths)-2]
file_proper=paths[n_elements(paths)-1]

logfile=ctime+'/'+ctime+'.log'

user_status = auto_setup_userword(rc)
spawn,'ramp_sq1_fb '+file_name+' '+string(rc)+ ' >> /data/cryo/current_data/'+logfile,exit_status=status13
if status13 ne 0 then begin
        print,''
        print,'######################################################################'
        print,'# ERROR! AN ERROR HAS OCCURED WHEN RUNNING THE RAMP_SQ1 CHECK SCRIPT #'
        print,'######################################################################'
        print,''
        exit,status=13
endif

cd = ''
;Set filename.
full_name=folder+date+file_name
openr, 3, '/data/cryo/current_data_name'
readf, 3,  cd
close, 3
name_label = '/data/cryo' + '/' + cd + '/' + file_name 


; Register ramp acquisition
rf = mas_runfile(full_name+'.run')
n_frames = mas_runparam(rf,'FRAMEACQ','DATA_FRAMECOUNT',/long)
reg_status = auto_setup_register(acq_id, 'tune_ramp', full_name, n_frames)

; Call analysis / plotting routine
plot_file = folder + date + 'analysis/' +file_name + '.ps'
sq1ramp = auto_setup_analysis_ramp_sq1_fb(full_name, plot_file=plot_file, $
                                          rows=rows, extra_labels=extra_labels)

; Share results via the common block (boo)
new_adc_offset = sq1ramp.adc_offset
squid_p2p = sq1ramp.p2p
squid_lockrange = sq1ramp.lockrange
squid_lockslope = sq1ramp.lockslope
squid_multilock = sq1ramp.multilock

; Archive the rampc and rampb files.

if keyword_set(poster) then $
   auto_post_plot,poster,filename=file_proper+'.ps'
   
if not keyword_set(quiet) then begin
    print,' '
    print,'###########################################################################'
    print,' '
    print,'To view the SQ1 V-phi curves check the file'
    print,string(plot_file)
    print,' '
    print,'###########################################################################'
endif

close, 3
if keyword_set(interactive) then spawn, 'ggv '+plot_file+' &'
fine:
end
