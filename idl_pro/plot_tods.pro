
PRO plot_tods,dir=dir,file

;--------------------------------------------------------------------------------------------------------------------------
; read MCE data using mas_data.pro
; plot tods
;--------------------------------------------------------------------------------------------------------------------------

close,/all
start_mem=MEMORY(/current)
;----------------------------------------------------------------------------------------------------------------
;path='/data/cryo/current_data/'
;pathp='/data/cryo/current_data/analysis/'

file=dialog_pickfile(get_path=filepath,path='/data/cryo/current_data/',/must_exist,/read)
;filename=path+dir+'/'+file
;-------------------------------------------------------------------------------------------------------------------
;header information
;------------------------------------------------------------------------------------------------------------------

;frame_info = create_struct( $
;                            'version',     header(6), $
;                            'row_len',     header(2), $
;                            'num_rows_rep',header(3), $
;                            'data_rate',   header(4), $
;                            'num_rows',    header(9), $
;                            'rc_present',  rc_present, $
;                            'rc_count',    rc_count, $
;                            'n_frames',    0L, $ ; place holder
;                            'n_columns',   8L*rc_count, $
;                            'n_rows',      header(3), $
;                            'frame_size',  0L, $ ; place holder
;                            'data_size',   0L, $ ; place holder
;                            'footer_size', 1L, $
;                            'data_offset', 43L $
;)

;------------------------------------------------------------------------------------------------------------------
data=mas_data(file,frame_info=frame_info)
;---------------------------------------------------------------------------------------------------------------
; converts fb to Volts ---> FB1 is 14bit and Vout_max=1V
;--------------------------------------------------------------------------------------------------------------
data=data/2.^14*0.965          ; Volt --  Vout_max=0.965 for BICEP2 MCE

;###########################################################################################################################

n_col=frame_info.n_columns
n_row=frame_info.n_rows
npts=frame_info.n_frames

set_plot,'ps'
device,filename='/data/cryo/current_data/analysis/tods.ps',/landscape,/color
;loadct,13
!p.multi=[0,4,4]
;################################################################################

for i = 0, 15 do begin

   for j = 0, n_row-1 do begin

plot,data[i,j,*],thick=6,charthick=5.0,charsize=1.3,psym=2,symsize=0.5,ytitle='FB(Volt)',title='Col'+strtrim(i,1)+' Row'+strtrim(j,1),/yno

 endfor                  ; end loop on n_row 
 endfor                  ; end loop on n_col

device,/close
set_plot,'x'

print,'memory required',MEMORY(/highwater)-start_mem

stop
end
