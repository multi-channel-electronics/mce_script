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

def get_curve_regions(y, extremality=0.8,
                      pairs=False,
                      extrema=False,
                      extremum=0,
                      slopes=False,
                      slope=0):
    """
    Analyzes the 1-d array y into ranges that are identified either as
    "hi", "lo", or in transition.
    
    Returns a list of indices into y.  These indices indicate the
    start positions of each group of hi, hi-to-lo, lo, and lo-to-hi
    regions in the curve.

    The number of indices returned is always a multiple of 4.  The
    first index is always 0, and is the starting index of a "hi"
    group.

    When indices are repeated it indicates an empty region; so a curve
    that starts with a lo spanning 0:100 will return indices
       [0,0,0,100,...]

    When the pairs=True, the indices are converted into pairs suitable
    for range indexing.  I.e.  [0,10,45,70] would be transformed to
       [(0,10),(10,45),(45,70),(70,len(y))]

    Particular regions can be selected by passing any one of:
      extrema=True    return only the hi and lo regions.
      extremum=+-1    return only the hi or lo regions, depending on sign
      slopes=True     return only the transition regions.
      slope=+-1       return only the rising or falling transition regions.
    Setting one of these keywords sets pairs=True implicitly.
    """
    y1, y0 = y.max(), y.min()
    y0, dy = 0.5*(y1+y0), 0.5*(y1-y0)
    if dy == 0:
        dy = 1
    y = (y - y0)/dy  # Now in [-1,+1]
    # Identify samples in extreme regions.
    n = len(y)
    hi = hstack(((y >  extremality).nonzero()[0], n))
    lo = hstack(((y < -extremality).nonzero()[0], n))

    # Reduce the list to starts and stops
    idx = 0
    transitions = []
    while idx < n:
        transitions.append(idx)
        if hi[0] == idx:
            idx = hi[hi<lo[0]][-1]+1
            hi = hi[hi>=lo[0]]
        transitions.append(idx)
        if lo[0] <= hi[0]:
            idx = lo[0]
        transitions.append(idx)
        if lo[0] == idx:
            idx = min(n,lo[lo<=hi[0]][-1]+1)
            lo = lo[lo>=hi[0]]
        transitions.append(idx)
        if hi[0] <= lo[0]:
            idx = hi[0]

    def pairify():
        return zip(transitions, transitions[1:]+[len(y)])
    
    if extrema:
        return pairify()[::2]
    if slopes:
        return pairify()[1::2]
    if slope < 0:
        return pairify()[1::4]
    if slope > 0:
        return pairify()[3::4]
    if extremum > 0:
        return pairify()[0::4]
    if extremum < 0:
        return pairify()[2::4]
    if pairs:
        return pairify()
    return transitions


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
    #! This should be rewritten to use get_curve_regions.
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
            # Take nearest low-point, or 0 if there isn't one.
            right_idx = hstack(((yy<=-extremality).nonzero()[0],0))[0]
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
        #corr /= (y[:,-width:].std(axis=1)**2).reshape(-1,1) # OLD
        corr /= amin(corr[:,width:],axis=1).reshape(-1,1)
    return corr

def period(y, width=None):
    """
    Determine periods of (V-phi) curves in y (a 2-d array).

    This algorithm will work best when width is ~phi0/2.  The curves
    in y should contain at least (phi0 + width).

    Expect failures when running with small 'width' on curves that
    have bad composition multi-lock features.
    """
    n0, n_x = y.shape
    if width == None:
        width = n_x / 8
    p = zeros(n0)
    # Get the correlations, and locate their second minimum
    corr = period_correlation(y, width=width, normalize=False)
    for i, c in enumerate(corr):
        for tol in [0.1, 0.2, 0.3, 0.4]:  #allow for noisier curves
            tr = get_curve_regions(c, tol, extremum=-1)
            # Exit the loop if we get a good lock on the first minimum
            if len(tr) > 1 and tr[1][0] != tr[1][1]:
                break
        else:
            # Couldn't find the auto-corr's next minimum, give up
            p[i] = 0
            continue
        i0,i1 = tr[1]
        p[i] = i0 + argmin(c[i0:i1])
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
         format=None,
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
                
    pl = util.plotGridder(y_rc, plot_file, title=title,
                          xlabel=xlabel, ylabel=ylabel,
                          target_shape=shape, img_size=img_size,
                          col_labels=cl, rowcol_labels=rcl,
                          format=format)
            
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

    pl.cleanup()
    return {
        'plot_files': pl.plot_files,
        }
