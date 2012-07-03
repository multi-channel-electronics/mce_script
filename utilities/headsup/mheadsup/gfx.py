import numpy as np

def grid_coords(nrow, ncol):
    # boring
    c = np.arange(ncol)
    r = np.arange(nrow)
    x = (c + r[...,None]*0).ravel()
    y = (c*0 + r[...,None]).ravel()
    return x, y
    
def circle_coords(nrow, ncol, spacing=1.4):
    N = nrow*ncol
    A = spacing*N
    a = np.arange(float(N))/N * A
    r = (a/np.pi)**.5
    R, PHI = np.ceil(r), (r - np.ceil(r))*2*np.pi
    return R*np.cos(PHI), R*np.sin(PHI)

