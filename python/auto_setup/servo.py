import auto_setup.util as util
from numpy import *
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
    # Remove mean!
    y = y - y.mean(axis=1)[:,None]
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


"""
SquidData - base class for tuning stage analysis objects.
"""

class SquidData(util.RCData):
    stage_name = 'SquidData'
    xlabel = 'X'
    ylabels = {'data': 'Y'}

    def __init__(self, tuning=None):
        util.RCData.__init__(self)
        self.data = None
        self.analysis = None
        self.tuning = tuning

    @classmethod
    def join(cls, args):
        """
        Merge a list of objects of type cls into a new cls.
        """
        synth = cls(tuning=args[0].tuning)
        # Borrow most things from the first argument
        synth.mcefile = None
        synth.data_origin = dict(args[0].data_origin)
        synth.fb = args[0].fb.copy()
        synth.d_fb = args[0].d_fb
        synth.bias_style = args[0].bias_style
        synth.bias = args[0].bias.copy()

        # Join data systematically
        util.RCData.join(synth, args)
        return synth

    def _check_data(self, simple=False):
        if self.data == None:
            raise RuntimeError, '%s needs data.' % self.stage_name
        if simple and self.gridded:
            raise RuntimeError, 'Simple %s expected (use split?)' % \
                self.stage_name

    def _check_analysis(self, existence=False):
        if self.analysis == None:
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
        if fb == None:
            fb = arange(self.data.shape[-1])
        self.fb = fb
        self.d_fb = fb[1] - fb[0]
        if len(self.data_shape) > 3:
            self.bias_style = 'ramp'
            self.bias = bias
            if self.bias == None:
                self.bias = arange(self.data_shape[-3])
        else:
            self.bias_style = 'select'
            self.bias = bias
            if self.bias == None:
                self.bias = zeros(n_col,'int')
        self.mcefile = None
        self.rf = None

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
            s.bias = ones(self.cols.shape, 'int')*self.bias[i]
            output.append(s)
        return output

    def select_biases(self, indices=None):
        """
        Reduce the servo data by selecting certain curves from
        super-entries in each column.
        """
        if indices == None:
            self._check_analysis()
            indices = self.analysis['y_span_select']
        # Get a single-bias servo
        s = self.split()[0]
        s.bias_style = 'select'
        for i, j in enumerate(indices):
            s.bias[i] = self.bias[j]
        # Make sure to reduce each data attribute
        for k in self.data_attrs:
            src, dest = getattr(self, k), getattr(s, k)
            src.shape, dest.shape = self.data_shape, s.data_shape
            for i, j in enumerate(indices):
                dest[:,i,:] = src[j,:,i,:]
            src.shape, dest.shape = (-1, self.data_shape[-1]), (-1, s.data_shape[-1])
        return s

    def reduce(self, slope=None):
        self.reduce1()
        self.reduce2(slope=slope)
        return self.analysis

    def reduce1(self):
        """
        Compute peak-to-peak response, store in self.analysis.
        """
        self._check_data()
        self._check_analysis(existence=True)
        span = amax(self.data, axis=-1) - amin(self.data, axis=-1)
        self.analysis['y_span'] = span
        if self.bias_style == 'ramp':
            # Identify bias index of largest response in each column
            select = span.reshape(self.data_shape[:-1]).max(axis=-2).argmax(axis=0)
            self.analysis['y_span_select'] = select
        return self.analysis
    
    def reduce2(self, slope=None):
        raise RuntimeError, "this is a virtual method."

    def plot(self, plot_file=None, format=None, data_attr='data'):
        if plot_file == None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))
        if format == None:
            format = self.tuning.get_exp_param('tuning_plot_format')

        # Is this a multi-bias ramp?  If so, split down
        if self.bias_style == 'ramp':
            ss = self.split()
            plot_files = []
            _format = format
            if format == 'pdf':  # make one big pdf
                _format = 'svg'
            for i,s in enumerate(ss):
                s.reduce()
                p = s.plot(plot_file=plot_file+'_%02i'%i, format=_format,
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
