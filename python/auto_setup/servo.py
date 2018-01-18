import auto_setup.util as util
from numpy import *
import numpy as np
import biggles
import os

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
                    start=None, stop=None, extremality=0.9,
                    x_adjust=None):
    # By default, we characterize the extrema ignoring the beginning
    # of the curve, since the servo may still be settling.
    if start is None:
        start = y.shape[1]/8
    if stop is None:
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
        if left_idx >= right_idx:
            left_idx, right_idx = 0,0
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
        # User may need to move the setpoint around, for whatever reason.
        if x_adjust is not None and not all(x_adjust==0):
            lock_idx += x_adjust
            target = array([yy[i] for yy,i in zip(y, lock_idx)])
        # Compute lock slopes and sub-sample the locking X-values.
        lock_slope, dx = get_slopes(y-target.reshape(-1,1),
                                    lock_idx, intercept='x', n_points=scale,
                                    min_index=i_left, max_index=i_right)
        lock_y = array([yy[i] for i,yy in zip(lock_idx, y)])
    else:  # x
        lock_idx = (i_left + i_right)/2
        if x_adjust is not None:
            lock_idx += x_adjust
        lock_slope, lock_y = get_slopes(y, lock_idx, intercept='y',
                                        n_points=scale,
                                        min_index=i_left, max_index=i_right)
        dx = zeros(y.shape[0])
    
    n_locks = []
    for ok, yy, lidx in zip(oks, y, lock_idx):
        if not ok:
            n = 0
        else:
            # find all slopy regions
            locks = [array([max(0,x[0]), min(len(yy)-1,x[1])])
                     for x in get_curve_regions(yy, slopes=True, extremality=extremality)
                     if x[0] != x[1]]
            # count the regions that cross the lock point
            n = sum([(min(yy[x])<yy[lidx] and max(yy[x])>yy[lidx]) for x in locks])
        n_locks.append(n)

    return {'lock_idx': lock_idx,
            'lock_didx': dx,
            'lock_y': lock_y,
            'lock_slope': lock_slope,
            'slope': slope,
            'left_idx': i_left,
            'right_idx': i_right,
            'lock_count': array(n_locks),
            'ok': array(oks)
            }


def get_slopes(data, index, n_points=5, min_index=None, max_index=None,
               intercept=None):
    """
    Fit straight line to data (a 2-d array) in vicinity of index (a
    1-d array).  Return slopes (a 1-d array).
    """
    if min_index is None:
        min_index = zeros(data.shape[0])
    if max_index is None:
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
    if intercept is None:
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
    # Remove mean!
    y = y - y.mean(axis=1)[:,None]
    if width is None:
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
    if width is None:
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
            if m is not None:
                if y0 is None:
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
        if insets is not None:
            ax.add(biggles.PlotLabel(0., 0., insets[i],
                                         halign='left',valign='bottom'))
        if x.shape==y.shape:
            ax.add(biggles.Curve(x[i]/1000., y[i]/1000.))
        else:
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
            if x.shape==y.shape:
                ax.xrange = x[i][0]/1000., x[i][-1]/1000.
            else:
                ax.xrange = x[0]/1000., x[-1]/1000.                

    pl.cleanup()
    return {
        'plot_files': pl.plot_files,
        }


"""
SquidData - base class for tuning stage analysis objects.
"""

class SquidData(util.RCData):
    stage_name = 'SquidData'
    xlabel = 'X'
    ylabels = {'data': 'Y'}

    # Are 'select' biases associated with column or row?
    bias_assoc = 'col'

    def __init__(self, tuning=None):
        util.RCData.__init__(self)
        self.data = None
        self.analysis = None
        if isinstance(tuning, basestring):
            tuning = util.tuning.tuningData(exp_file=tuning)
        self.tuning = tuning

    @classmethod
    def join(cls, args, target=None):
        """
        Merge a list of objects of type cls into a new cls.
        """
        synth = target
        if synth is None:
            synth = cls(tuning=args[0].tuning)
        
        # Borrow most things from the first argument
        synth.mcefile = None
        synth.data_origin = dict(args[0].data_origin)
        synth.fb = args[0].fb.copy()
        synth.d_fb = args[0].d_fb
        synth.bias_style = args[0].bias_style
        synth.bias_assoc = args[0].bias_assoc
        if synth.bias_style == 'select':
            synth.bias = np.hstack([a.bias for a in args])
        else:
            synth.bias = args[0].bias.copy()

        # Join data systematically
        util.RCData.join(synth, args)
        return synth

    def _check_data(self, simple=False):
        if self.data is None:
            raise RuntimeError, '%s needs data.' % self.stage_name
        if simple and self.gridded:
            raise RuntimeError, 'Simple %s expected (use split?)' % \
                self.stage_name

    def _check_analysis(self, existence=False):
        if self.analysis is None:
            if existence:
                self.analysis = {}
            else:
                raise RuntimeError, '%s lacks desired analysis structure.' % \
                    self.stage_name

    def reduce_rows(self):
        """
        Average along rows dimension.
        """
        s = list(self.data_shape)
        n_r, n_c, n_fb = s[-3:]
        self.data.shape = (-1, n_r, n_c, n_fb)
        self.data = self.data.astype('float').mean(axis=-3).reshape(-1, n_fb)
        s[-3] = 1
        self.data_shape = s
        self.rows = [-1]

    def from_array(self, data, shape=None, fb=None, bias=None, origin='array'):
        """
        Load V-phi data from an array, for testing or whatever.
        """
        self.data_shape = data.shape
        self.data_origin = {'filename': origin,
                            'basename': origin }
        while len(self.data_shape) < 3:
            self.data_shape = (1,) + self.data_shape
        self.data = data.reshape(-1, data.shape[-1])
        n_row, n_col = self.data_shape[-3:-1]
        self.gridded = True
        self.cols = array([i for i in range(n_col)])
        self.rows = array([i for i in range(n_row)])
        if fb is None:
            fb = arange(self.data.shape[-1])
        self.fb = fb
        self.d_fb = fb[1] - fb[0]
        if len(self.data_shape) > 3:
            self.bias_style = 'ramp'
            self.bias = bias
            if self.bias is None:
                self.bias = arange(self.data_shape[-3])
        else:
            self.bias_style = 'select'
            self.bias = bias
            if self.bias is None:
                self.bias = zeros(n_col,'int')
        self.mcefile = None
        self.rf = None

    def load_ramp_params(self, bias_key, servo_par_bug=False):
        """
        Parse runfile loop declaration to determine feedback and bias
        values applied.  Requries self.rf and self.cols to already be set.

        bias_key should be the runfile parameter (in HEADER) where the
        applied bias can be found, in cases where the bias is not
        being ramped.
        """
        rf = self.rf
        rcs = rf.Item('FRAMEACQ', 'RC', type='int')
        self.cols = array([i+(rc-1)*8 for rc in rcs for i in range(8)])

        # Fix me: sometimes runfile always indicates bias was ramped,
        # even though it usually wasn't
        bias_ramp = (rf.Item('par_ramp', 'par_title loop1 par1', \
                                 array=False).strip().endswith('bias'))

        ## This helps a bit... or does it.  When this key exists and
        ## is set, it means that that loop1 should be ignored.
        bias_ramp_active = rf.Item('par_ramp', 'par_active loop1 par1',
                                   array=False, type='int')
        if bias_ramp_active is None:
            bias_ramp_active = bias_ramp

        if bias_ramp:
            bias0, d_bias, n_bias = rf.Item('par_ramp', 'par_step loop1 par1',
                                            type='int')
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop2 par1',
                                      type='int')
            self.bias_style = 'ramp'
            self.bias = bias0 + d_bias*arange(n_bias)
        else:
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1',
                                      type='int')
            n_bias = 1
        # This should just extend the else; the second clause is a bug work-around
        if not bias_ramp or \
                (servo_par_bug and (bias_ramp and n_bias == 1)) or \
                not bias_ramp_active:
            self.bias_style = 'select'
            self.bias = array(rf.Item('HEADER', bias_key, type='int'))[self.cols]

        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb

        # New block!  Ya.
        self.super_servo = rf.Item('servo_params', 'super_servo',
                                   array=False, type='int')

    def _read_super_bias(self, filename):
        """
        Helper for read_data that assembles array of data from all-row
        .bias files.
        """
        f = filename + '.bias'
        index_set, self.error, self.data = util.load_super_bias_file(f)
        n_bias, n_fb, n_row = amax(index_set, axis=1)+1
        # Reshape and transpose time axis to the end
        n_col = self.error.shape[0]
        self.error, self.data = [ \
            d.reshape(n_col, n_bias, n_fb, n_row). \
                transpose([1,3,0,2]). \
                reshape(-1, n_fb) for d in [self.error, self.data]]
        self.data_shape = (n_bias, n_row, n_col, n_fb)
        self.gridded = True
        self.rows = index_set[2,:n_row]

    def read_data(self, filename, **kwargs):
        raise RuntimeError, "this is a virtual method"

    def split(self):
        """
        Split multi-bias data (from combined bias+fb ramp) into single
        objects per bias.  Returns a list of single bias ramps.
        """
        if self.bias_style == 'select':
            return [self]

        n_bias, n_row, n_col, n_fb = self.data_shape
        copy_keys = ['data_origin', 'rows', 'cols', 'fb', 'd_fb',
                     'tuning', 'mcefile', 'rf']
        output = []
        for i in range(n_bias):
            s = self.__class__()
            # Copy basic keys, or set to None.
            for k in copy_keys:
                setattr(s, k, getattr(self, k, None))
            # Copy data arrays
            for k in self.data_attrs:
                data = getattr(self, k)
                setattr(s, k, data.reshape(n_bias, -1)[i].reshape(-1, n_fb))
            s.data_shape = self.data_shape[1:]
            s.gridded = True
            s.bias_style = 'select'
            if self.bias_assoc == 'col':
                s.bias = ones(n_col, 'int')*self.bias[i]
            elif self.bias_assoc == 'row':
                s.bias = ones(n_row, 'int')*self.bias[i]
            elif self.bias_assoc == 'rowcol':
                s.bias = ones(n_row*n_col, 'int')*self.bias[i]
            output.append(s)
        return output

    def select_biases(self, bias_idx=None, assoc=None, ic_factor=None):
        """
        Reduce bias-ramp V-phi data to bias-select data, by selecting
        a particular bias index for each row, column, or (row,col)
        pair.  Returns an object of the same type.

        If ic_factor != 1., the chosen bias will be the peak bias
        scaled by ic_factor, though limited to be within the bias
        range of the ramp.  The resulting V-phi data in this case is
        an interpolation between the curves of the nearest bias
        points.
        """
        if self.bias_style == 'select':
            # This object does not contain per-bias data.
            return None # or self?

        if ic_factor is None:
            ic_factor = 1.0;
        
        # How many biases are we selecting here?  This is described
        # bias self.bias_assoc, declared by each subclass.  We will
        # use this to shuffle the array dimensions around so that
        # axis=1 is the axis over which bias will be optimized.
        if assoc is None:
            assoc = self.bias_assoc

        self.analysis['select_assoc'] = assoc
        n_bias, n_row, n_col, n_fb = self.data_shape

        transpose_row_col = False
        if assoc == 'rowcol':
            n_group, n_member = n_row*n_col, 1
        elif assoc == 'col':
            n_group, n_member = n_col, n_row
            transpose_row_col = True
        elif assoc == 'row':
            n_group, n_member = n_row, n_col
        else:
            raise ValueError, "cannot select_bias with assoc='%'" % assoc

        # If the user has not passed in the desired indices into the
        # bias array, try to find it in the analysis.
        if bias_idx is None:
            k = 'select_%s_sel'%assoc
            bias_idx = self.analysis[k]

        # Get a cheap single-bias servo
        s = self.split()[0]
        s.bias_style = 'select'
        s.bias_assoc = assoc

        def get_curves(key, idx0, idx1, assoc=None):
            d = getattr(self, key).reshape(n_bias, n_row, n_col, n_fb)
            if assoc=='rowcol':
                d = getattr(self, key).reshape(n_bias, n_row*n_col, n_fb)
            if transpose_row_col:
                d = d.transpose((0,2,1,3))
            return d[idx0,idx1].reshape(n_member, n_fb)

        # Reduced V-phi data
        for k in self.data_attrs:
            setattr(s, k, np.zeros((n_group, n_member, n_fb)))
            
        for i in range(n_group):
            # Keep bias in range
            bias = self.bias[bias_idx][i] * ic_factor
            s.bias[i] = max(self.bias[0], min(bias, self.bias[-1]))
            idx0 = (self.bias[:-1] <= bias).nonzero()[0][-1]
            frac = float(s.bias[i] - self.bias[idx0]) / \
                (self.bias[idx0+1] - self.bias[idx0])

            # chokes if bias_assoc='rowcol'
            # Interpolate between two curves
            for k in self.data_attrs:
                d0 = get_curves(k, idx0, i, assoc)
                d1 = get_curves(k, idx0+1, i, assoc)
                getattr(s, k)[i] = d0*(1-frac) + d1*frac

        # Possibly transpose and reshape
        for k in self.data_attrs:
            d = getattr(s, k)
            if transpose_row_col:
                d = d.transpose((1,0,2))
            setattr(s, k, d.reshape(-1, n_fb))

        return s

    def get_selection_ramp(self):
        # This better be a ramp
        if not self.bias_style == 'ramp':
            return RuntimeError, \
                "get_selection_ramp only valid for bias ramps."
        # Get curve amplitudes as fn of bias
        nb, nr, nc, n = self.data_shape
        span = self.analysis['y_span'].reshape(nb, nr, nc).\
            transpose(axes=(1,2,0))
        brs = biasRampSummary()
        brs.from_array(span, fb=self.bias)
        return brs

    def reduce(self, slope=None):
        self.reduce1()
        self.reduce2(slope=slope)
        return self.analysis

    def reduce1(self, slope=None):
        """
        Compute peak-to-peak response, store in self.analysis.
        """
        self._check_data()
        self._check_analysis(existence=True)
        mx, mn = amax(self.data, axis=-1), amin(self.data, axis=-1)
        self.analysis['y_max'] = mx
        self.analysis['y_min'] = mn
        self.analysis['y_span'] = mx - mn
        if self.bias_style == 'ramp':
            # Identify bias index of largest response in each column
            select = (mx-mn).reshape(self.data_shape[:-1])\
                .max(axis=-2).argmax(axis=0)
            # Scale by ic_factor.  I guess we have to round it.
            self.analysis['select_col_sel'] = select
        return self.analysis
    
    def reduce2(self, slope=None):
        raise RuntimeError, "this is a virtual method."

    def plot(self, plot_file=None, format=None, data_attr='data'):
        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))
        if format is None:
            format = self.tuning.get_exp_param('tuning_plot_format',
                                               default='png')

        # Is this a multi-bias ramp?  If so, split down
        if self.bias_style == 'ramp':
            ss = self.split()
            plot_files = []
            _format = format
            if format == 'pdf':  # make one big pdf
                _format = 'svg'
            for i,s in enumerate(ss):
                s.reduce()
                p = s.plot(plot_file=plot_file+'_b%02i'%i, format=_format,
                           data_attr=data_attr)
                plot_files += p['plot_files']
            # collate into pdf?
            if format == 'pdf':
                ofile = plot_file + '_all.pdf'
                pp = util.plotter.pdfCollator(plot_files, ofile)
                if pp.collate(remove_sources=True):
                    plot_files = [ofile]
            return {'plot_files': plot_files}

        # Now worry about whether we have analysis and data...
        self._check_data()
        self._check_analysis()

        # Display biases as inset text
        insets = ['BIAS = %5i' % x for x in self.bias]

        # Default data is self.data
        data = getattr(self, data_attr)
    
        # Plot plot plot
        return plot(
            self.fb, data, self.data_shape[-3:-1],
            self.analysis, plot_file,
            shape=(4, 2),
            slopes=True,
            insets=insets,
            title=self.data_origin['basename'],
            xlabel=self.xlabel,
            ylabel=self.ylabels[data_attr],
            format=format,
            )

class RampSummary(SquidData):
    """
    Base class for summarizing analysis results from, e.g. multiple
    biases.  For example, after getting V-phi curves at several biases
    one might like to plot some statistic (such as the peak-to-peak
    amplitude) vs. bias.

    This provides initialization and plotting facilities, but leaves
    loading of the data to subclasses.
    """
    xlabel = 'BIAS / 1000'

    def __init__(self):
        SquidData.__init__(self)

    @classmethod
    def from_biases(cls, parent):
        # Check parent for compatibility
        if parent.bias_style != 'ramp':
            raise ValueError, "parent is not a bias ramp!"
        # What do we have here
        n_bias, n_row, n_col, n_fb = parent.data_shape
        self = cls()
        self.data_shape = (1, n_row, n_col, n_bias)
        self.data_origin = parent.data_origin
        self.tuning = parent.tuning
        self.cols = np.array(parent.cols, copy=True)
        self.rows = np.array(parent.rows, copy=True)
        self.gridded = True
        self.bias = None
        self.bias_style = 'select'
        self.bias_assoc = parent.bias_assoc
        self.fb = parent.bias.copy()
        self.data = {}
        self.ylabels = {}
        return self

    def add_data(self, name, data, ylabel='Stat'):
        # Assume incoming data is parent's bias,nrow,ncol shape.
        n_row, n_col, n_bias = self.data_shape[-3:]
        self.data[name] = data.reshape(n_bias, n_row, n_col)\
            .transpose((1,2,0)).reshape(-1, n_bias)
        self.ylabels[name] = ylabel

    def plot(self, plot_file=None, format=None, data_attr=None):
        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s_summary' % \
                                         (self.data_origin['basename']))
        if format is None:
            format = self.tuning.get_exp_param('tuning_plot_format',
                                               default='png')

        if data_attr is None:
            data_attr = 'y_span'
        data = self.data[data_attr]
    
        # Plot plot plot
        return plot(
            self.fb, data, self.data_shape[-3:-1],
            self.analysis, plot_file,
            shape=(4, 2),
            slopes=False,
            lock_levels=False,
            set_points=True,
            title=self.data_origin['basename'],
            xlabel=self.xlabel,
            ylabel=self.ylabels[data_attr],
            format=format,
            )
        

if __name__ == '__main__':
    from random import random
    # Get some fake data
    N = 100
    x = arange(N)
    y = []
    F = [2.2, 1.3, 0., 10.]
    for f in F:
        a, b, p = random() * 1000, (random()-.5)*10000, random()*N
        y.append(a * sin(2*pi*x*f/N+p) + b)
    y = array(y)
    print 'Periods:  ', period(y)
    print 'Expected: ', N/array(F)
    lp = get_lock_points(y, slope=array([1,1,1,-1]))
    print 'Lock-x: ', lp['lock_idx']
    reg = []
    for yy in y:
        reg.append(get_curve_regions(yy, slopes=True))
        print 'Crossings: ', reg[-1]
    print 'Plotting...'
    fp = biggles.Table(2,2)
    for i in range(4):
        p = biggles.FramedPlot()
        p.add(biggles.Curve(x, y[i]))
        p.add(biggles.LineX(x[lp['lock_idx'][i]],type='dashed'))
        p.add(biggles.LineY(lp['lock_y'][i],type='dashed'))
        p.yrange = y[i].min()-10, y[i].max()+10
        fp[i%2,i/2] = p
    fp.write_img(500,500, 'check_servo.png')
