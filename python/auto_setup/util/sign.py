import math
from numpy import *

def sign(x):
    if hasattr(x, "__getitem__") and (not hasattr(x, "ndim") or x.ndim > 0):
        return array([sign(y) for y in x]);
    else:
        if x > 0 or (x == 0 and math.atan2(x, -1.) > 0.):
            return 1
        else:
            return -1
