import mce_data
interactive = False
if not interactive:
    from matplotlib import use
    use('Agg')

from pylab import *
import sys
from glob import glob


def read(filename, trim=None):
    f = mce_data.SmallMCEFile(filename)
    d = f.Read(row_col=True)
    nr,nc,nt = d.data.shape
    c = d.data.reshape(nr, -1).transpose().reshape(nc, -1)
    if trim:
        c = c[:,trim[0]:trim[1]]
    return c

def plot_group_mean(file_spec, outdir='./', trim=None):
    files = glob(file_spec)
    for i,f in enumerate(files):
        d = read(f,trim=trim)
        dd = mean(d, axis=0).reshape(1,-1)
        clf()
        power(dd,0)
        title('%s - mean of 8 columns'%f)
        savefig('%s/power_%02i.png'%(outdir,i))
        clf()
        time(dd,0)
        savefig('%s/time_%02i.png'%(outdir,i))

def time(data, col):
    plot(data[col])
    show()

def power(data, col, xlimits=None):
    n = len(data[col])
    df = 50./n
    f = df*arange(n/2)
    p = abs(fft(data[col]))[0:n/2] #*df
    subplot(2,1,1)
    loglog(f[1:], p[1:])
    if xlimits!=None:
        xlim(xlimits)
    subplot(2,1,2)
    plot(f[1:], p[1:])
    if xlimits!=None:
        xlim(xlimits)
    show()

if __name__ == '__main__':
    fn = sys.argv[1]
    d = read(fn)
