pro auto_setup_plot_servo, plot_file, $
   x_data, y_data, err_data, lock_x, lock_y, points=points,$
   xtitle=xtitle, ytitle=ytitle, errtitle=errtitle, $
   plot_titles=plot_titles, errplot_titles=errplot_titles, page_title=page_title, $
   col_start=col_start, col_count=col_count, range_start=range_start

; x_data should 

n_x = n_elements(x_data)

if not keyword_set(title) then title=plot_file
if not keyword_set(xtitle) then xtitle='Input'
if not keyword_set(ytitle) then ytitle='Output'
if not keyword_set(errtitle) then errtitle='Error'
if not keyword_set(col_start) then col_start = 0
if not keyword_set(col_count) then col_count = 8
if not keyword_set(range_start) then range_start = 10


set_plot, 'ps'
device, filename= plot_file, /landscape
!p.multi=[0,2,4]

for j = 0, col_count - 1 do begin
   ymin = min(y_data[j,range_start:*])
   ymax = max(y_data[j,range_start:*])
   if keyword_set(plot_titles) then begin
      if n_elements(plot_titles) eq 1 then stitle = plot_titles $
      else stitle = plot_titles[j]
   endif else stitle = ''
   plot, x_data, y_data[j,*], $
         /xs, /ys, yrange=[ymin, ymax], $
         xtitle=xtitle, ytitle=ytitle, title=stitle

   if keyword_set(points) then begin
      ; Show lock point positions
      oplot, [lock_x[j], lock_x[j]], [ymin, ymax]
      oplot, [x_data[0], x_data[n_x-1]], [lock_y[j], lock_y[j]]
   endif else begin
      ; Plot the error signal
      ymin = min(err_data[j,range_start:*])
      ymax = max(err_data[j,range_start:*])
      if keyword_set(errplot_titles) then begin
         if n_elements(errplot_titles) eq 1 then stitle = errplot_titles $
         else stitle = errplot_titles[j]
      endif else stitle = ''

      plot, x_data, err_data[j,*], $
            /xs, /ys, yrange=[ymin, ymax], $
            xtitle=xtitle, ytitle=ytitle, title=stitle
   endelse

endfor

device, /close                  ;close ps

end
