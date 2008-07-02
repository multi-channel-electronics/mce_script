function mas_runparam,data,block,tag,error=error,long=long,float=float, $
                      array=array,format=format

; MAS_RUNPARAM
;
; Returns the data associated with a run file entry.
;
; Usage:
;     result = mas_runparam, data, block, tag, error=error
;
;     data       The runfile structure returned by mas_runfile
;     block      The desired block name
;     tag        The desired tag name
;     error      Set to 0 on success, -1 if the block was not found,
;                -2 if the block was found but the tag was not.
;
;     long       Convert the key text to an array of long integers.
;     float      Convert the key text to an array of floats.
;     array      Load a set of tags, whose names are defined by the
;                format keyword, and return the result in a 2-d
;                array.
;     format     When the 'array' keyword is passed, the format is
;                used to construct the tag names that are loaded to
;                populate the array.  By default the format will be
;                constructed from the tag by appending integers 0, 1,
;                ...  to the end of the tag.
;
; Returns:
;     The key text associated with the desired block/tag, or -1 on
;     failure.
;
;     The key is returned as a single string unless one or more of the
;     long, float, or array keywords are activated.
;

error = -1

; Catch array keyword and recurse (only once, don't worry about it...)

if keyword_set(array) then begin
    if not keyword_set(format) then format = '("'+tag+'",I0)'

    ; Find first key and items
    sub_tag = string(format=format, 0)
    k = mas_runparam(data, block, sub_tag, long=long, float=float, error=error)
    if error ne 0 then return,k
    n_rows = n_elements(k)

    ; Assume 50 lines at first, make it bigger or smaller as required.
    n_lines_max = 1
    n_lines = 1
    kk = replicate(k[0], [n_lines_max, n_rows])

    ; Calling runparam here is slower than it needs to be, we could
    ; fly down the list ourself...
    
    while 1 do begin
        
        sub_tag = string(format=format, n_lines)
        k = mas_runparam(data, block, sub_tag, long=long, float=float, error=line_error)

        if line_error ne 0 then $
          return, kk[0:n_lines-1,*]

        if n_lines eq n_lines_max then begin
            ; Double the size of the storage array.
            n_lines_max = n_lines_max * 2
            old_kk = kk
            kk = replicate(k[0], [n_lines_max, n_rows])
            kk[0:n_lines-1,*] = old_kk
        endif

        kk[n_lines,*] = k
        n_lines = n_lines + 1

    endwhile

    return,kk
    
endif

; Single entry processing

b_idx = where(data.blocks eq block)
if b_idx eq -1 then return,-1

tag_idx = [[data.tag_indices], n_elements(data.tags)]
tags = data.tags(tag_idx(b_idx):(tag_idx(b_idx+1) - 1))
keys = data.keys(tag_idx(b_idx):(tag_idx(b_idx+1) - 1))

t_idx = where(tags eq tag)
if t_idx eq -1 then return,-2
t_idx = t_idx[0]

error=0

if keyword_set(long)  then return, long(strsplit(keys[t_idx],/extract))
if keyword_set(float) then return, float(strsplit(keys[t_idx],/extract))

return,keys[t_idx]

end
