pro plot_sq2servo,sq2,column
; sq2 is a struct returned by read_bias_data.pro

n_bias = n_elements(sq2.bias)
n_fb = n_elements(sq2.fb)

ylo = min(sq2.y[column,*,*])
yhi = max(sq2.y[column,*,*])
ylo = ylo - 0.15*(yhi-ylo)  ; to make room for labels.

plot_title=sq2.filename + '  Column:' + string(column, format='(I2)')

plot,[0,n_bias*n_fb],[ylo,yhi],/nodata,/ynozero, title=plot_title
;plot,sq2.y[column,*,*]

print,'bias_idx        index        bias   pk-pk'
for b=0,n_bias-1 do begin
    oplot,indgen(n_fb) + n_fb*b,sq2.y[column,b,*]
    oplot,[1,1]*(n_fb*(b+1)), [ylo, yhi];,color=255
    xyouts,n_fb*(b+0.7), ylo, '!6'+string(sq2.bias[b],format='(i5)'), alignment=1., orientation=90.
    print,b,n_fb*b,sq2.bias[b],max(sq2.y[column,b,*])-min(sq2.y[column,b,*])
endfor

end
