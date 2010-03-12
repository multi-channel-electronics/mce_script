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
    print y.shape, yscale.shape, y_min.shape, y_max.shape, dy.shape
    # Find all ineligible points with opposite derivative
    other_edge = (dy*slope < 0) #* \
    z = \
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


class plotMap:
    def __init__(self, plot_shape, data_shape):
        self.ps = plot_shape,
        self.ds = data_shape
        self.pn = self.ps[0]*self.ps[1]
    
    def data_rc(self, p_page, p_idx):
        # row, col
        i = p_page * self.pn + p_idx
        return i / self.ds[1], i % self.ds[1]

    def stack_title(self, p_page, p_col):
        r, c = self.data_rc(p_page, p_col*self.ps[0])
        dc = self.data_rc(p_page, (p_col+1)*self.ps[0]-1)

def plot1(x, y, lock_points, plot_file,
         shape=(4,4), scale=1./1000,
         title=None, xlabel=None, ylabel=None,
         titles=None,
         rows=None, cols=None,
         insets=None,
         lock_levels=True,
         set_points=False,
         intervals=False,
         slopes=False):
    n_plots = y.shape[0]
    for a in ['xlabel', 'ylabel', 'titles']:
        if eval(a) == None or type(eval(a)) == str:
            exec('%s=[%s]*n_plots' % (a,a))
    per_page = shape[0] * shape[1]
    n_pages = (n_plots + per_page) / per_page
    print n_pages, n_plots, len(xlabel)

    for page in range(n_pages):
        p = util.tuningPlotStack(shape[0], shape[1], multi=True,
                                 title=title)
        for j in range(per_page):
            i = page*per_page + j
            if i >= n_plots: break
            
            ax = p.subplot(title=titles[i], xlabel=xlabel[i], ylabel=ylabel[i])
            if set_points:
                ax.add(biggles.LineX(lock_points['lock_x'][i]*scale))
            if lock_levels:
                ax.add(biggles.LineY(lock_points['lock_y'][i]*scale))
            if intervals:
                ax.add(biggles.LineX(lock_points['left_x'][i]*scale,type='dashed'))
                ax.add(biggles.LineX(lock_points['right_x'][i]*scale,type='dashed'))
            if slopes:
                for d in ['up', 'dn']:
                    m,x0,y0 = [lock_points['lock_%s'%(e)][i]
                               for e in ['%s_sl'%d,'%s_x'%d,'y']]
                    ax.add(biggles.Slope(m, (x0*scale,y0*scale),type='dashed'))
            if insets != None:
                print insets[i]
                ax.add(biggles.PlotLabel(0., 0., insets[i],
                                         halign='left',valign='bottom'))
            ax.add(biggles.Curve(x/1000., y[i]/1000.))
            # Prevent small signals from causing large tick labels
            hi, lo = amax(y[i])/1000, amin(y[i])/1000
            if hi - lo < 4:
                mid = (hi+lo)/2
                ax.yrange = (mid-2, mid+2)
        p.set_stack_props(title=['Col %i' % i for i in range(4)])
        filename = plot_file % page
        p.save(filename)
    
def plot(x, y, y_rc, lock_points, plot_file,
         shape=(4,2), scale=1./1000,
         title=None, xlabel=None, ylabel=None,
         titles=None,
         rows=None, cols=None,
         insets=None,
         lock_levels=True,
         set_points=False,
         intervals=False,
         slopes=False):

    print y_rc
    nr, nc = y_rc
    pl = util.plotGridder(y_rc, plot_file, title=title, xlabel=xlabel, ylabel=ylabel,
                          target_shape=shape, col_labels=True)
            
    for r, c, ax in pl:
        i = c + r*nc
        print r, c, i
        if set_points:
            ax.add(biggles.LineX(lock_points['lock_x'][i]*scale))
        if lock_levels:
            ax.add(biggles.LineY(lock_points['lock_y'][i]*scale))
        if intervals:
            ax.add(biggles.LineX(lock_points['left_x'][i]*scale,type='dashed'))
            ax.add(biggles.LineX(lock_points['right_x'][i]*scale,type='dashed'))
        if slopes:
            for d in ['up', 'dn']:
                m,x0,y0 = [lock_points['lock_%s'%(e)][i]
                           for e in ['%s_sl'%d,'%s_x'%d,'y']]
                ax.add(biggles.Slope(m, (x0*scale,y0*scale),type='dashed'))
        if insets != None:
            ax.add(biggles.PlotLabel(0., 0., insets[i],
                                         halign='left',valign='bottom'))
        ax.add(biggles.Curve(x/1000., y[i]/1000.))
        # Prevent small signals from causing large tick labels
        hi, lo = amax(y[i])/1000, amin(y[i])/1000
        if hi - lo < 4:
            mid = (hi+lo)/2
            ax.yrange = (mid-2, mid+2)

