from __future__ import division
from past.utils import old_div
import numpy as np

def grid_coords(nrow, ncol):
    # boring
    c = np.arange(ncol)
    r = np.arange(nrow)
    x = (c + r[...,None]*0).ravel()
    y = (c*0 + r[...,None]).ravel()
    return x - x.mean(), y - y.mean()
    
def circle_coords(nrow, ncol, spacing=1.4):
    N = nrow*ncol
    R = (old_div(N,np.pi))**.5
    a = old_div(np.arange(float(N)),N)
    r = a**.5 * R
    R, PHI = spacing * (np.floor(r)+1), (r - np.floor(r))*2*np.pi
    return R*np.cos(PHI), R*np.sin(PHI)

