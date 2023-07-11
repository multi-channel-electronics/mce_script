from __future__ import division
from past.utils import old_div
from numpy import *

def logbin(f, y, bins=400):
    """
    Rebin frequency vector f and power spectrum y with a logarithmic
    bin distribution.  Returns new_f, new_y with

       new_f  -  centre of frequency bins (mean of contributors)
       new_y  -  spectrum at new_f (RMS of contributors)

    Actually, f doesn't have to be a vector -- it can just be a float
    containing the upper frequency bound.
    """
    if not hasattr(f, '__getitem__'):
        # Convert to vector [0, f)
        f = f * arange(y.shape[0]) / y.shape[0]
    df = f[1] - f[0]
    f_max = f[-1] + df
    f_min = f[1]
    N = log(old_div(f_max, f_min))
    dN = old_div(N, bins)
    edges = f_min * exp(dN * arange(bins+1))
    # Frequency counts for norming
    nf = histogram(f, bins=edges)[0]
    # Central frequency and binned power
    new_f = histogram(f, weights=f, bins=edges)[0]
    new_y = histogram(f, weights=abs(y)**2, bins=edges)[0]
    # Reduce
    new_f = old_div(new_f[nf!=0], nf[nf!=0])
    new_y = sqrt(old_div(new_y[nf!=0],nf[nf!=0]))
    return new_f, new_y



# Test
if __name__ == '__main__':
    from pylab import *
    from todUtils import TOD
    filename = '/scr/queequeg1/colossus/season2/merlin/20081013/1223886429.1234568432.ar1'
    tod = TOD.read(filename, camCol=[5], camRow=[25])
    x, y = arange(old_div(tod.ndata,2), dtype='float') / tod.ndata * 400., \
           abs(fft(tod.data[0]))[:old_div(tod.ndata,2)]
    x1, y1 = logbin(x, y)
    x2, y2 = logbin(200., y)
    loglog(x, y)
    loglog(x1, y1)
    loglog(x2, y2)
    show()
