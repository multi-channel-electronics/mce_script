#!/usr/bin/python

try:
    from pylab import *
    plotter = 'pylab'
except:
    print 'pylab absent, trying biggles.'
    import biggles as bg
    plotter = 'biggles'

from numpy import *

from mce_data import *
import sys, os
from glob import glob

from logbin import logbin

def file_info(fn):
    d = MCEFile(fn+'.run')
    rc = rf.Item('FRAMEACQ','RC',type='int',array=False)
    chan = rf.Item('Column','RC',type='int',array=False)

def load_raw_file(fn, kill_partial=33, drop_initial=1):
    d = MCEFile(fn).Read()
    d.data = d.data[:,0:65000]
    return d

def power(data):
    n = len(data)
    df = 50.e6 / n
    p = abs(fft.fft(data)[0:n/2]) / sqrt(50.e6*n)
    p[0] = 0.
    f = df * arange(n/2)
    return f, p

def time_series(files, column=0):
    ts = []
    for fn in files:
        d = load_raw_file(fn)
        if not check_data(d.data):
            print 'Weird data in %s'%fn
        ts.append(d.data[column,:])
    return ts

def spectra(files, column=0):
    spectra = []
    for fn in files:
        d = load_raw_file(fn)
        if not check_data(d.data):
            print 'Weird data in %s'%fn
        f, p = power(d.data[column,:65536])
        spectra.append(p)
    return f, array(spectra)

def check_data(data):
    mx = amax(data, axis=1)
    mn = amin(data, axis=1)
    return (sum((abs(mx-mn) > 1e3).astype('int')) <= 0)

def ident(x):
    return x

#T_1 = log
#T_2 = exp
T_1 = ident
T_2 = ident


def model(x, p):
    #f0, f1, f2, A, B, beta0, beta1, beta2 = p
    A, B, f0, beta0, f1, beta1 = p
#    A, B, f0, f1, f2, f3 = p
#    return (T_1(B + A*abs(1./(1+1j*(x/f0))/(1+1j*(x/f1))/(1+1j*(x/f2))/(1+1j*(x/f3)))))
    return (T_1(B + A*abs(1./(1+1j*(x/f0)**beta0)/(1+1j*(x/f1)**beta1)))) # / (1+(x/f2)**beta2))

def resid(*args):
    p = args[0]
    x, y = args[1:]
    return y - model(x, p)

def model_3db(p):
    f = arange(.1e6, 10e6, .1e6)
    y = model(f, p) / model(f[:1], p)[0]
    idx = (y < 0.5).nonzero()[0][0]
    return f[idx]

if __name__ == '__main__':
    from optparse import OptionParser
    o = OptionParser()
    o.add_option('--plot', default='show',
                 help='PNG filename or "show" to show.')
    opts, args = o.parse_args()

    if len(args) == 1 and os.path.isdir(args[0]):
        files = glob('%s/*raw' % args[0])
        if len(files) == 0:
            print 'No files found in directory "%s"' % args[0]
            sys.exit(1)
    else:
        files = args
        if len(files) == 0:
            print 'Give directory or filenames.'
            sys.exit(1)

    # Column is always 0 for one-RC raw grabs.
    column = 0
    n_files = len(files)
    ts = time_series(files, column)

    print 'Computing RMS for %i files.' % n_files
    rr = [t.std() for t in ts]
    print 'RMS:                     ', mean(rr), ' +- ', std(rr)
        
    # Load spectra, average bin.
    f, p = spectra(files, column)
    pr = sqrt(mean(p**2, axis=0))
    f2, y2 = logbin(f, pr, bins=1000)

    # Scale to be n_pts invariant
    
    # Levels levels levels
    white_cut = 0.1e6
    high_cut = 15e6
    white_level = sqrt(mean(p[:,f<white_cut]**2))
    high_level = sqrt(mean(p[:,f>high_cut]**2))

    print 'White noise (ADC/rtHz):  ', white_level
    print 'Noise floor (ADC/rtHz):  ', high_level
    print 'Ratio:                   ', high_level / white_level

    # Find 3dB
    f3db_level = white_level / sqrt(2.)
    search_cut = 0.5e6
    f3db = f2[((f2 > search_cut)*(y2 <= f3db_level)).nonzero()][0]

    print 'f_3db (MHz):             ', f3db/1e6, 'MHz'

    # Plot plot plot.
    if plotter == 'pylab':
        loglog(f2, y2)
        plot([1e3, white_cut], [white_level]*2)
        plot([high_cut, 25e6], [high_level]*2)
        plot([f3db]*2, [high_level, white_level])
        xlim(1e3, 2.5e7)
        if opts.plot == 'show':
            show()
        else:
            savefig(opts.plot)
    else:
        fp = bg.FramedPlot()
        fp.x1.log = 1
        fp.y1.log = 1
        fp.add(bg.Curve(f2, y2))
        fp.add(bg.Curve([1e3, white_cut], [white_level]*2))
        fp.add(bg.Curve([high_cut, 25e6], [high_level]*2))
        fp.add(bg.Curve([f3db]*2, [high_level, white_level]))
        if opts.plot == 'show':
            fp.show()
        else:
            fp.write_img(600, 500, opts.plot)

