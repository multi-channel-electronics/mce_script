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

def get_lock_points(y, scale=5, lock_amp=False, slope=1.,
                    start=None, stop=None, extremality=0.9):
    # By default, we characterize the extrema ignoring the beginning
    # of the curve, since the servo may still be settling.
    if start == None:
        start = y.shape[1]/8
    if stop == None:
        stop = y.shape[1]

    y1, y0 = y[:,start:stop].max(axis=1).astype('float'), \
        y[:,start:stop].min(axis=1).astype('float')
    mids = ((y1+y0)/2).reshape(-1,1)
    amps = ((y1-y0)/2).reshape(-1,1)
    amps[amps==0] = 1.

    # Copy data, rescaled to +-1 and corrected for slope.
    slope = sign(array(slope)).reshape(-1,1)
    y2 = slope * (y.astype('float') - mids) / amps

    # For each curve, identify a pair of adjacent extrema
    ranges = []
    oks = []
    for yy in y2:
        # Find high points
        ok = True
        right_idx = (yy>=extremality).nonzero()[0]
        if len(right_idx) == 0:  # probably a flat-liner?
            right_idx = array([len(yy)-1])
            ok = False
        # Find low points left of right-most high point:
        left_idx = (yy[:right_idx[-1]]<=-extremality).nonzero()[0]
        if len(left_idx) > 0:
            # Great, take right-most low point and then the next high point.
            left_idx = left_idx[-1]
            right_idx = min(right_idx[right_idx>=left_idx])
        else:
            # This is a bad curve, so we're just trying to cope somehow
            ok = False
            left_idx = right_idx[-1]
            right_idx = (yy<=-extremality).nonzero()[0][0]
        ranges.append((left_idx, right_idx))
        oks.append(ok)
    i_left, i_right = array(ranges).transpose()

    # Lock mid-way in y or x?
    if lock_amp:  # y
        target = array([yy[a] + yy[b] for yy,a,b in \
                            zip(y, i_left, i_right)]) / 2
        lock_idx = array([a + argmin(abs(yy[a:b+1]-t)) for \
                          a,b,t,yy in zip(i_left, i_right, target, y)]) \
                          .astype('int')
        # Compute lock slopes and sub-sample the locking X-values.
        lock_slope, dx = get_slopes(y-target.reshape(-1,1),
                                    lock_idx, intercept='x', n_points=scale,
                                    min_index=i_left, max_index=i_right)
        lock_y = array([yy[i] for i,yy in zip(lock_idx, y)])
    else:  # x
        lock_idx = (i_left + i_right)/2
        lock_slope, lock_y = get_slopes(y, lock_idx, intercept='y',
                                        n_points=scale,
                                        min_index=i_left, max_index=i_right)
        dx = zeros(y.shape[0])

    return {'lock_idx': lock_idx,
            'lock_didx': dx,
            'lock_y': lock_y,
            'lock_slope': lock_slope,
            'slope': slope,
            'left_idx': i_left,
            'right_idx': i_right,
            'ok': array(oks)
            }


def get_slopes(data, index, n_points=5, min_index=None, max_index=None,
               intercept=None):
    """
    Fit straight line to data (a 2-d array) in vicinity of index (a
    1-d array).  Return slopes (a 1-d array).
    """
    if min_index == None:
        min_index = zeros(data.shape[0])
    if max_index == None:
        max_index = [d.shape[-1] for d in data]
    
    fits = []
    for d, i, lo, hi in zip(data, index, min_index, max_index):
        sl_idx = arange(max(lo, i-n_points/2),
                        min(hi, i+(n_points+1)/2))
        if len(sl_idx) < 2:
            fits.append([0.,0.])
        else:
            fits.append(polyfit(sl_idx-i, d[sl_idx], 1))
    fits = array(fits).transpose()
    if intercept == None:
        return fits[0]  # slope only
    if intercept == 'y':
        return fits[0], fits[1]
    if intercept == 'x':
        x0 = - fits[1] / fits[0]
        x0[fits[0]==0] = 0.
        return fits[0], x0
    raise ValueError, 'Invalid intercept request "%s"' % intercept


def period_correlation(y, width=None, normalize=True):
    n, nx = y.shape
    if width == None:
        width = nx / 2
    m = nx - width
    corr = zeros((n, m))
    for i in range(m):
        corr[:,i] = sum((y[:,nx-width-i:nx-i] - y[:,-width:])**2, axis=1)
    if normalize:
        # at some point we have to cross the other slope
        corr /= (y[:,-width:].std(axis=1)**2).reshape(-1,1)
    return corr

def period(y, width=None):
    """
    Determine periods of (V-phi) curves in y.
    """
    n0, n_x = y.shape
    if width == None:
        width = n_x / 2
    p = zeros(n0)
    corr = period_correlation(y, width=width)
    for i, c in enumerate(corr):
        # Each corr curve rises up from 0 to some maximum, then down
        # to "0" again, and repeat (or not).
        thresh = 3. # units are rms**2
        dc = c - thresh
        ups = ((dc[1:] > 0) * (dc[:-1] <= 0)).nonzero()[0]
        dns = ((dc[1:] < 0) * (dc[:-1] >= 0)).nonzero()[0]
        if len(ups) < 1 or len(dns) < 1:
            continue
        if len(ups) < 2: ups = [ups[0], len(c)]
        p[i] = dns[0] + argmin(c[dns[0]:ups[1]])
    return p

def add_curves(ax, x, y, lp, i,
               set_points=True, lock_levels=True, intervals=True,
               slopes=True, insets=True):
    if set_points and lp.haskey('lock_x'):
        ax.add(biggles.LineX(lp['lock_x'][i]*scale))
    if lock_levels and lp.haskey('lock_y'):
        ax.add(biggles.LineY(lp['lock_y'][i]*scale))
    if intervals and lp.haskey('left_x'):
        ax.add(biggles.LineX(lp['left_x'][i]*scale,type='dashed'))
    if intervals and lp.haskey('right_x'):
        ax.add(biggles.LineX(lp['right_x'][i]*scale,type='dashed'))
    if slopes:
        for d in ['up', 'dn']:
            if not lp.haskey('lock_%s_sl' % d): continue
            m,x0,y0 = [lp['lock_%s'%(e)][i]
                       for e in ['%s_sl'%d,'%s_x'%d,'y']]
            ax.add(biggles.Slope(m, (x0*scale,y0*scale),type='dashed'))


def plot(x, y, y_rc, lock_points, plot_file,
         shape=(4,2), img_size=None, scale=1./1000,
         title=None, xlabel=None, ylabel=None,
         titles=None,
         rows=None, cols=None,
         insets=None,
         lock_levels=True,
         set_points=False,
         intervals=False,
         slopes=False,
         scale_style='tight',
         label_style='row_col',
         ):

    nr, nc = y_rc
    cl, rl, rcl = False, False, False
    if label_style == 'col_only':
        cl = True
    elif label_style == 'row_col':
        rcl = True

    if slopes == True:
        def get(key, param):
            return lock_points.get('lock_%s%s' % (key,param), None)
        slopes = []
        for d in ['', 'up_', 'dn_']:
            m, x0, y0 = [get(d, p) for p in ['slope', 'x', 'y']]
            if m != None:
                if y0 == None:
                    # Use default y-target if separate up/dn aren't there.
                    y0 = get('', 'y')
                slopes.append(zip(m, x0, y0))
                
    pl = util.plotGridder(y_rc, plot_file, title=title, xlabel=xlabel, ylabel=ylabel,
                          target_shape=shape, img_size=img_size,
                          col_labels=cl, rowcol_labels=rcl)
            
    for r, c, ax in pl:
        if r >= nr or c >= nc: continue
        i = c + r*nc
        if set_points:
            ax.add(biggles.LineX(lock_points['lock_x'][i]*scale))
        if lock_levels:
            ax.add(biggles.LineY(lock_points['lock_y'][i]*scale))
        if intervals:
            ax.add(biggles.LineX(lock_points['left_x'][i]*scale,type='dashed'))
            ax.add(biggles.LineX(lock_points['right_x'][i]*scale,type='dashed'))
        if slopes != False:
            for s in slopes:
                m, x0, y0 = s[i]
                ax.add(biggles.Slope(m, (x0*scale,y0*scale),type='dashed'))
        if insets != None:
            ax.add(biggles.PlotLabel(0., 0., insets[i],
                                         halign='left',valign='bottom'))
        ax.add(biggles.Curve(x/1000., y[i]/1000.))

        if scale_style == 'roll-off':
            # Prevent small signals from causing large tick labels
            hi, lo = amax(y[i])/1000, amin(y[i])/1000
            if hi - lo < 4:
                mid = (hi+lo)/2
                ax.yrange = (mid-2, mid+2)
        elif scale_style == 'tight':
            hi, lo = amax(y[i]) / 1000., amin(y[i]) / 1000.
            dx = (hi - lo)*.1
            ax.yrange = lo - dx, hi + dx
            ax.xrange = x[0]/1000., x[-1]/1000.
    return {
        'plot_files': pl.plot_files,
        }
