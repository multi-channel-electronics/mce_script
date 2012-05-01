; What kind of language requires this much work to implement a sign function?

function sign,x,nozero=nozero
  temp = x
  idx = where(temp eq 0)
  if idx[0] ne -1 then $
    temp[where(temp eq 0)] = 1.
  if keyword_set(nozero) then return, temp/abs(temp) $
  else return, x/abs(temp)
end
