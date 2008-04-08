function remove_jumps,data_in,jump_size,threshold=threshold,up_only=up_only,down_only=down_only

if not keyword_set(threshold) then threshold = jump_size / 2

data = float(data_in)

ind = indgen(n_elements(data) - 1)
delta = float(data(ind+1)) - float(data(ind))
adjust = 1
downs = where(delta lt -threshold) + adjust
ups   = where(delta gt  threshold) + adjust

if not keyword_set(up_only) and (downs(0) ne -1 + adjust) then $
  for d=0,n_elements(downs)-1 do $
  data(downs(d):*) = data(downs(d):*) + jump_size

if not keyword_set(down_only) and (ups(0) ne -1 + adjust) then $
  for u=0,n_elements(ups)-1 do $
  data(ups(u):*) = data(ups(u):*) - jump_size

return,data

end
