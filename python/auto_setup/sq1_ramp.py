from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import zip
from builtins import range
from past.utils import old_div
import os, time
from mce_data import MCEFile, MCERunfile
from numpy import *
import auto_setup.idl_compat as idl_compat
import auto_setup.util as util
import auto_setup.servo as servo

def go(tuning, rc, filename=None, slope=None, flags=None):
    ok, ramp_data = acquire(tuning, rc, filename=filename, do_bias=do_bias)
    if not ok:
        raise RuntimeError(servo_data['error'])

    s = sq1_ramp(filename)
    s.reduce1()
    s.reduce2()
    s.plot(tuning=tuning)

    # Translate analysis dictionary
    a = s.analysis
    n_col = s.data_shape[1]
    return {'new_adc_offset': a['lock_y'].reshape(-1,n_col),
            'squid_p2p': (a['max_y'] - a['min_y']).reshape(-1,n_col),
            'squid lockslope': vstack((a['lock_dn_slope'],
                                       a['lock_up_slope'])).reshape(2,-1,n_col),
            }

def acquire(tuning, rc, filename=None, check=False):
    # File defaults
    if filename is None:
        action = 'sq1ramp'
        if check: action = 'sq1rampc'
        filename, acq_id = tuning.filename(rc=rc, action=action)
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Execute ramp
    cmd = ['ramp_sq1_fb', filename, rc]
    status = tuning.run(cmd)
    if status != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.base_dir, filename)
    rf = MCERunfile(fullname + '.run')
    n_frames = rf.Item('FRAMEACQ','DATA_FRAMECOUNT',type='int',array=False)
    tuning.register(acq_id, 'tune_ramp', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename':fullname,
                  'rc': rc,
                  }

def acquire_tes_ramp(tuning, rc, filename=None):
    # File defaults
    if filename is None:
        action = 'sq1ramptes'
        filename, acq_id = tuning.filename(rc=rc, action=action)
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Execute ramp
    cmd = ['ramp_sq1_tes_bias', filename, rc]
    status = tuning.run(cmd)
    if status != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.base_dir, filename)
    rf = MCERunfile(fullname + '.run')
    n_frames = rf.Item('FRAMEACQ','DATA_FRAMECOUNT',type='int',array=False)
    tuning.register(acq_id, 'tune_ramp', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename':fullname,
                  'rc': rc,
                  }

def get_lock_slope(data, index, slope_points=5):
    """
    Fit straight line to data in vicinity of index.  Return x
    intercept and slope.
    """
    sl_idx = arange(max(0, index-slope_points),
                    min(len(data), index+slope_points+1))
    if len(sl_idx) == 0: return 0., 0.
    if len(sl_idx) == 1: return sl_idx[0], 0.
    p = polyfit(sl_idx, data[sl_idx], 1)
    return old_div(-p[1],p[0]), p[0]

def get_lock_points(data, slope=None, max_points=5, min_spacing=5):
    """
    Find zero-crossings of data.  Return positions, spaced by at least
    min_spacing.
    """
    if slope is None:
        slope = [1,-1]
    else:
        slope = [slope]
    # Zero crossings
    z = []
    for s in slope:
        z.extend(((data[:-1]*s < 0) * (data[1:]*s >= 0)).nonzero()[0])
    z.sort()
    if min_spacing is None: return array(z)
    # Eliminate proximations
    idx = 1
    while idx < min(max_points+1, len(z)):
        if z[idx] - z[idx-1] < min_spacing:
            z.pop(idx)
        else:
            idx += 1
    return array(z)


def lock_stats(data, target=0., range=None, slope=1.,
               slope_properties=True, slope_points=5, flag=False):
    """
    Analyze V-phi curve in data, return position and character of lock
    points.
    """
    n_times = len(data)
    if range is None: range = (0, n_times)
    L = get_lock_points(data[range[0]:range[1]]-target, slope=slope)
    ok = len(L) > 0
    if ok: L = L[0]
    else: L = 0
    if not slope_properties:
        return ok, L+range[0]
    else:
        if not ok:
            return ok, range[0], 0
        a, m = get_lock_slope(data-target, L+range[0], slope_points=slope_points)
        if flag: print(L, range, a, m)
        return ok, a, m



class SQ1Ramp(util.RCData):

    xlabel = 'SQ1 FB / 1000'
    ylabel = 'AD Units / 1000'

    def __init__(self, filename=None, tuning=None):
        util.RCData.__init__(self)
        self.data = None
        self.analysis = None
        self.tuning = tuning
        if filename is not None:
            self.read_data(filename)

    @classmethod
    def join(cls, args):
        """
        Arguments are SQ1Ramp (or inheritor) objects, loaded with data.
        """
        synth = cls(tuning=args[0].tuning)
        # Borrow most things from the first argument
        synth.mcefile = None
        synth.data_origin = dict(args[0].data_origin)
        synth.fb = args[0].fb.copy()
        synth.d_fb = args[0].d_fb

        synth.bias_style = args[0].bias_style
        synth.bias = args[0].bias

        # Join data systematically
        util.RCData.join(synth, args)
        return synth

    def _check_data(self):
       if self.data is None:
            raise RuntimeError('sq1_ramp needs data.')

    def _check_analysis(self):
       if self.analysis is None:
            raise RuntimeError('sq1_ramp needs analysis.')

    def read_data(self, filename):
        self.mcefile = MCEFile(filename)
        self.data = self.mcefile.Read(row_col=True).data
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}
        self.gridded = True
        self.data_shape = self.data.shape
        # Ravel.
        self.data.shape = (-1, self.data.shape[-1])
        # Record the rows and columns, roughly
        rcs = self.mcefile.runfile.Item('FRAMEACQ', 'RC', type='int')
        self.cols = array([i+(rc-1)*8 for rc in rcs for i in range(8)]).ravel()
        self.rows = array([i for i in arange(self.data_shape[0])])
        # Feedback vector.
        rf = self.mcefile.runfile
        fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb
        # We don't generally consider the bias at this stage
        self.bias_style = None
        self.bias = None            

    def reduce1(self, rule=None):
        """
        Finds curve amplitudes, locking levels, locking points.
        Creates analysis elements
               {min,max}_y
               {left,right}_idx
               lock_{idx,y,count}
        """
        if rule is None:
            rule = self.tuning.get_exp_param('sq1_ramp_locking_rule',
                                             default='y_space_sorted')
        print(rule)

        self._check_data()
        # Analyze every single stupid rampc curve
        scale = max([old_div(len(self.fb),40), 1])
        y = servo.smooth(self.data, scale)
        x_offset = old_div(scale,2)
        dy  = y[:,1:] - y[:,:-1]
        y   = y[:,:-1]

        # Simple way to find local extrema
        Thi = ((dy[:,1:] < 0)*(dy[:,:-1] >= 0))
        Tlo = ((dy[:,1:] > 0)*(dy[:,:-1] <= 0))
        
        # Indices of extrema, by det.
        Tex = [x.nonzero()[0] for x in Thi+Tlo]
        # No empty curves allowed
        for i in range(len(Tex)):
            if len(Tex[i]) == 0:
                Tex[i] = [0, 1]

        clear_lims = False
        if rule=='x_space':
            # Find widest region between extrema
            dT = [ x[1:] - x[:-1] for x in Tex ]
            widx = [ argmax(x) for x in dT ]
            lims = [ (x[i], x[i+1]) for x,i in zip(Tex, widx) ]
        elif rule == 'y_space':
            # Find largest y-separation between adjacent local extrema
            lims = []
            for T_set, yy in zip(Tex, y):
                z = [(yy[x], x) for x in T_set]
                dz = [a[0] - b[0] for a, b in zip(z[1:],z[:-1])]
                idx = argmax(dz)
                lims.append((z[idx][1], z[idx+1][1]))
        elif rule == 'y_space_sorted':
            # Take y coordinates of all extrema, sort them, and
            # identify the largest uninterrupted interval.  This can
            # help avoid multi-locking in some cases.  We do not
            # bother obtaining "lims" in this case.
            clear_lims = True
            lims = []
            for T_set, yy in zip(Tex, y):
                z = sorted([(yy[x], x) for x in T_set])
                dz = [a[0] - b[0] for a, b in zip(z[1:],z[:-1])]
                if len(dz) == 0:
                    lims.append((0,0))
                else:
                    idx = argmax(dz)
                    lims.append((z[idx][1], z[idx+1][1]))
                
        adc_offset = array([old_div((yy[a]+yy[b]),2) for (a,b),yy in zip(lims,y)])
        if clear_lims:
            lims = [(0,0)] * len(lims)

        # Good enough
        lock_left, lock_right = array(lims).transpose()
    
        result = {
            'max_y': amax(y, axis=1),
            'min_y': amin(y, axis=1),
            'lock_idx': old_div((lock_left + lock_right),2),
            'left_idx': lock_left,
            'right_idx': lock_right,
            'lock_y': adc_offset,
            }
        for k in ['lock', 'left', 'right']:
            result[k+'_idx'] += x_offset
            result[k+'_x'] = self.fb[result[k+'_idx']]
        result['rule'] = rule
        self.analysis = result
        return self.analysis

    def reduce2(self):
        """
        Measures slopes at lock points, creating analysis elements
               lock_{up,down}_{idx,x,sl,ok}

        Also gets phi0.
        """
        self._check_data()
        
        # Smooth
        scale = max([old_div(len(self.fb),40), 1])
        y = servo.smooth(self.data, scale)
        x_offset = old_div(scale,2)
        abs_lims = [-x_offset, len(self.fb)-x_offset-1]

        # Find lock points and slopes
        result = self.analysis
        #left = result['left_idx'] - x_offset
        targets = result['lock_y']
        for word, sgn in [('up', 1), ('dn',-1)]:
            ok, idx, sl, nl = [zeros(y.shape[0], x) for x in ['bool','int','float','int']]
            for i, (yy, t) in enumerate(zip(y, targets)):
                rg = (old_div(len(yy),4), len(yy))
                o, d, s = lock_stats(yy, target=t, slope_points=old_div(scale,2), slope=sgn,
                                     range=rg)
                d = max(0,min(len(yy)-1, d)) # Move in bounds.
                # Get curve regions
                regs = array(servo.get_curve_regions(yy))
                regs[regs>=len(yy)] = len(yy)-1
                regs = yy[regs] - t
                n = ((regs[1:]*regs[:-1] < 0) * (regs[1:]*sgn > 0)).sum()
                ok[i], idx[i], sl[i], nl[i] = o, d, s, n
            idx[idx<abs_lims[0]] = abs_lims[0]
            idx[idx>abs_lims[1]] = abs_lims[1]
            result['lock_%s_idx'%word] = idx + x_offset
            result['lock_%s_slope'%word] = old_div(sl, self.d_fb)
            result['lock_%s_ok'%word] = ok.astype('int')
            result['lock_%s_x'%word] = self.fb[result['lock_%s_idx'%word]]
            result['lock_%s_count'%word] = nl

        width = old_div(self.data.shape[-1], 4)
        phi0 = servo.period(self.data, width=width)
        result['phi0'] = phi0 * self.d_fb

        return result

    def reduce(self, rule=None):
        self.reduce1(rule=rule)
        self.reduce2()
        return self.analysis

    def plot(self, plot_file=None, dead_masks=None, format=None):
        self._check_data()
        self._check_analysis()

        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))

        nr, nc = self.data_shape[-3:-1]
        if dead_masks is not None:
            insets = ['' for i in range(nr*nc)]
            for dm in dead_masks:
                for i,d in enumerate(dm.data[:nr,:nc].ravel()):
                    if d > 0: insets[i] += dm.label + ' '
        else:
            insets = None

        if format is None:
            format = self.tuning.get_exp_param('tuning_plot_format')

        # Plot plot plot
        servo.plot(self.fb, self.data, (nr, nc),
                   self.analysis, plot_file,
                   shape=(8,4),
                   img_size=(900, 800),
                   insets=insets,
                   title=self.data_origin['basename'],
                   slopes=True, set_points=False, intervals=False,
                   xlabel=self.xlabel,
                   ylabel=self.ylabel,
                   scale_style='tight',
                   label_style='row_col',
                   format=format,
                   )

    def sqtune_report(self):
        """
        Return description of results for runfile block.
        """
        def get(key):
            return self.analysis[key].reshape(self.data_shape[-3:-1]).transpose()
        data = [
            {'label': 'vphi_p2p_C%02i',
             'data': get('max_y') - get('min_y'),
             'style': 'col_row', 'format': '%i', },
            {'label': 'vphi_phi0_C%02i',
             'data': get('phi0'),
             'style': 'col_row', 'format': '%i', },
            {'label': 'lock_range_C%02i',
             'data': get('right_x') - get('left_x'),
             'style': 'col_row', 'format': '%i', },
            {'label': 'lock_slope_down_C%02i',
             'data': get('lock_dn_slope'),
             'style': 'col_row', 'format': '%.3f', },
            {'label': 'lock_slope_up_C%02i',
             'data': get('lock_up_slope'),
             'style': 'col_row', 'format': '%.3f', },
            {'label': 'lock_count_dn_C%02i',
             'data': get('lock_dn_count'),
             'style': 'col_row', 'format': '%i', },
            {'label': 'lock_count_up_C%02i',
             'data': get('lock_up_count'),
             'style': 'col_row', 'format': '%i', },
#            {'label': 'Col%i_squid_multilock',
#             'data': get(''),
#             'style': 'col_row', 'format': '%i', },
#            {'label': 'Col%i_squid_off_recommendation',
#             'data': get(),
#             'style': 'col_row', 'format': '%i', },
            ]
        return {'block': 'SQUID_SQ1_RAMP', 'data': data}

class SQ1RampTes(SQ1Ramp):
    xlabel = 'TES bias / 1000'
