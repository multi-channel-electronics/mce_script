import math

def sign(x):
  if x > 0 or (x == 0 and math.atan2(x, -1.) > 0.):
    return 1
  else:
    return -1
