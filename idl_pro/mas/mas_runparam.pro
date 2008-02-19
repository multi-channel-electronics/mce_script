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
; Returns:
;     The key text associated with the desired block/tag, or -1 on
;     failure.
;


function mas_runparam,data,block,tag,error=error

error = -1

b_idx = where(data.blocks eq block)
if b_idx eq -1 then return,-1

tag_idx = [[data.tag_indices], n_elements(data.tags)]
tags = data.tags(tag_idx(b_idx):(tag_idx(b_idx+1) - 1))
keys = data.keys(tag_idx(b_idx):(tag_idx(b_idx+1) - 1))

t_idx = where(tags eq tag)
if t_idx eq -1 then return,-2
t_idx = t_idx[0]

error=0
return,keys[t_idx]

end
