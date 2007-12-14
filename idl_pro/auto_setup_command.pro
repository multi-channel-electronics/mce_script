pro auto_setup_command, software=software, command

if software eq 'DAS' then begin
	spawn,'mcecmd test wb '+command
endif else if software eq 'MAS' then begin
	spawn,'mce_cmd -q -x wb '+command
endif else begin
	print,'Acquisition software not recognized!'
	print,'Command: '+command+'did not go through.'
endelse

end
