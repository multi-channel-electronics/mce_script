import auto_setup.util as util
from numpy import *
import biggles

def smooth(x, scale):
    s = x.shape
    x.shape = (-1, s[-1])
    y = array([convolve(xx, [1]*scale, mode='valid') for xx in x]) / scale
    x.shape = s
    y.shape = s[:-1] + (y.shape[-1],)
    return y

def get_lock_points(data, scale=0, yscale=None, lock_amp=False, slope=1.):
    # Smooth, differentiate, and truncate to same length
    if scale > 0:
        y = smooth(data, scale)
    x_offset = (scale+1)/2      # Later we will compensate
    dy = y[:,1:] - y[:,:-1]
    y = y[:,:-1]

    # Find first extremum in second half.
    lo = y.shape[1] / 2
    hi = y.shape[1]

    # Measure y-extent
    y_max, y_min = y[:,lo:hi].max(axis=1), y[:,lo:hi].min(axis=1)
    y_mid, y_amp = (y_max + y_min)/2, (y_max - y_min)/2
    yscale = y_amp * 0.05

    # Find all ineligible points with opposite derivative
    other_edge = (dy*slope < 0) * \
        (y_max.reshape(-1,1) - y > yscale.reshape(-1,1)) * \
        (y - y_min.reshape(-1,1) > yscale.reshape(-1,1))

    # Find a rising or falling region
    if slope < 0:
        i_right = y[:,lo:hi].argmin(axis=1) + lo
    else:
        i_right = y[:,lo:hi].argmax(axis=1) + lo

    # Find right-most such point that is to the left of i_right
    i_left = i_right*0
    for i, (p, r) in enumerate(zip(other_edge, i_right)):
        if any(p[scale:r-scale/2]):
            i_left[i] = p[:r-scale/2].nonzero()[0][-1]
    
    # Lock mid-way in y or x?
    if lock_amp:
        target = array([yy[a] + yy[b] for yy,a,b in zip(y, i_left, i_right)]) / 2
        lock_idx = array([(slope*(yy[a:b]-tt)>=0).nonzero()[0][0]+a \
                              for a,b,tt,yy in zip(i_left, i_right, target, y)])
    else:
        lock_idx = (i_left + i_right)/2
    lock_y = array([yy[i] for i,yy in zip(lock_idx, y)])
    lock_idx += x_offset
    
    return {'lock_idx': lock_idx,
            'lock_y': lock_y,
            'slope': slope,
            'left_idx': i_left,
            'right_idx': i_right,
            }


def plot(x, y, lock_points, plot_file,
         title=None, xlabel=None, ylabel=None, titles=None):
    n_plots = y.shape[0]
    for a in ['xlabel', 'ylabel', 'titles']:
        if eval(a) == None or type(eval(a)) == str:
            exec('%s=[%s]*n_plots' % (a,a))
    print x.shape, y.shape
    n_pages = (n_plots + 7) / 8
    print n_pages, n_plots, len(xlabel)
    p = util.tuningPlot(4, 2, title=title, filename=plot_file, pages=n_pages)
    for page in range(n_pages):
        for j in range(8):
            i = page*8 + j
            if i >= n_plots: break
            ax = p.subplot(title=titles[i], xlabel=xlabel[i], ylabel=ylabel[i])
            ax.add(biggles.LineY(lock_points['lock_y'][i]/1000.))
            ax.add(biggles.LineX(lock_points['lock_x'][i]/1000.))
            ax.add(biggles.LineX(lock_points['left_x'][i]/1000.,type='dashed'))
            ax.add(biggles.LineX(lock_points['right_x'][i]/1000.,type='dashed'))
            ax.add(biggles.Curve(x/1000., y[i]/1000.))
        try:
            filename = plot_file % page
        except TypeError:
            filename = plot_file
        p.save(filename)
    
