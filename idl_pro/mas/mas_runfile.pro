; MAS_RUNFILE
;
; Loads MAS runfile data into a structure that can be parsed by mas_runparam.
;
; Usage:
;     result = mas_runfile ( filename )
;
;     filename   Path and name of the runfile to loaded.
;
; Returns:
;     The data block containing runfile data, or -1 on failure.
;


function str_recat,source

out=source(0)
for i=1,n_elements(source)-1 do $
  out = out+' '+source(i)

return, out
end


pro tag_split,source,tag,key

words = source   ; Make copy
words(0) = strmid(words(0), 1)  ; Remove the <
last_char=strmid(words,0,/reverse_offset)
last_tag_idx = where(last_char eq '>')
if n_elements(last_tag_idx) gt 1 then last_tag_idx = last_tag_idx(0)

words(last_tag_idx) = strmid(words(last_tag_idx), 0, strpos(words(last_tag_idx),'>',/reverse_search))
tag=str_recat(words(0:last_tag_idx))

if n_elements(words) le last_tag_idx+1 then $
  key = '' $
else $
  key = str_recat(words(last_tag_idx+1:*))

end


; MAS_RUNFILE
function mas_runfile,filename,data

openr,run_lun,filename,/get_lun

done = 0
count = 0
line=''

;Block loop
while not done do begin

    readf,run_lun,line
    if eof(run_lun) then done = 1

    words=strsplit(line,/extract)
    char1=strmid(words(0),0,1)
    if char1 ne '<' then continue
    
    tag_split,words, tag,key

    if not keyword_set(blocks) then begin
        blocks = tag
        tag_idx = 0
    endif else begin
        blocks = [ [blocks], tag ]
        tag_idx = [ [tag_idx], n_elements(tags) ]
    endelse

    while not done do begin
        readf,run_lun,line
        if eof(run_lun) then done = 1

        words=strsplit(line,/extract)
        char1=strmid(words(0),0,1)
        if char1 ne '<' then continue
        if strmid(words(0),1,1) eq '/' then break

        tag_split,words, tag, key
        if not keyword_set(tags) then begin
            tags = [ tag ]
            keys = [ key ]
        endif else begin
            tags = [ [tags ], [ tag ] ]
            keys = [ [keys ], [ key ] ]
        endelse

    endwhile

endwhile

free_lun,run_lun

data=create_struct('blocks',blocks,'tag_indices',tag_idx, 'tags',tags, 'keys',keys)

return, data

end
