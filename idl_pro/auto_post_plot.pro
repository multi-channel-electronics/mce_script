; AUTO_POST_PLOT
;
; Start a post_plot log:
;  auto_post_plot,poster,/open,dir='/data/cryo/current_data/1234000000',prefix='1234000000'
;
; Add files to the post_plot log:
;  auto_post_plot,poster,filename='1234000002_sq1ramp.ps'
; 
; Close the post_plot log and mark it as complete:
;  auto_post_plot,poster,/close
;

pro auto_post_plot,poster,filename=filename,prefix=prefix,open=open,close=close,dir=dir
  
  if keyword_set(open) then begin
     if not keyword_set(prefix) then prefix = './'
     poster = { prefix: prefix+'/', afile: dir + '/mceplots_archive', $
              closed: 0 }
     openw,lun,/get_lun,poster.afile
     printf,lun,'prefix '+poster.prefix
     free_lun,lun
     return
  endif

  if keyword_set(close) then begin
     poster.closed = 1
     openw,lun,/get_lun,/append,poster.afile
     printf,lun,'complete'
     free_lun,lun
     return
  endif

  ; Register this file
  openw,lun,/get_lun,/append,poster.afile
  printf,lun,'file '+filename
  free_lun,lun
     
end
