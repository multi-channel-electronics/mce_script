# This is a semitranslation of the IDL auto_setup_squids program.  The
# intent is to separate that program into three broad parts:
#
#  1) Data acquisition
#  2) Data Reduction and Tuning Calculations
#  3) Reporting (ie. Plots &c.)
#
# Because necessary data is stored after each of the above steps, it is 
# possible to run only part of the procedure, if the location of the output
# of previous step(s) is provided.

# -- Handy ruler ------------------------------------------------------|

import os, time
from mce_data import MCEFile, MCERunfile
from numpy import *
import auto_setup.idl_compat as idl_compat
import auto_setup.util as util
import auto_setup.servo as servo

def go(tuning, rc, filename=None, do_bias=None, slope=None):
    ok, ramp_data = acquire(tuning, rc, filename=filename, do_bias=do_bias)
    if not ok:
        raise RuntimeError, ramp_data['error']

    sa = SARamp(ramp_data['filename'], tuning=tuning)
    if sa.bias_style == 'ramp':
        sa.reduce1()
        sa = sa.subselect() # replace with best bias version

    lock_points = sa.reduce()
    plot_out = sa.plot()
    tuning.register_plots(*plot_out['plot_files'])
    
    # Return dictionary of relevant results
    return {'sa_bias': sa.bias,
            'fb': lock_points['lock_x'],
            'target': lock_points['lock_y'],
            }

def acquire(tuning, rc, filename=None, do_bias=None):
    # File defaults
    if filename == None:
        filename, acq_id = tuning.filename(rc=rc, action='ssa')
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Bias ramp default
    if do_bias == None:
        do_bias = tuning.get_exp_param('sa_ramp_bias')
        
    # Execute ramp
    cmd = ['ramp_sa_fb', filename, rc, int(do_bias)]
    status = tuning.run(cmd)
    if status:
        return False, {'error': 'command failed: %s with status %i' %
                (str(cmd), status)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.base_dir, filename)
    rf = MCERunfile(fullname + ".run")
    n_frames = rf.Item('FRAMEACQ','DATA_FRAMECOUNT',type='int',array=False)
    tuning.register(acq_id, 'tune_ramp', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename':fullname,
                  'rc': rc,
                  'do_bias': do_bias,
                  }


def get_set_point(y, dy=None, scale=5, slope=1.):
    if dy == None:
        dy = y[1:] - y[:1]
    if len(dy) != len(y):
        y = y[:len(dy)]
    n = len(y)

    # Find position of an SA minimum.  Search range depends on desired
    # locking slope because we will eventually need to find an SA max.
    if (slope > 0):
        min_start = scale * 4
        min_stop = n * 5 / 8
    else:
        min_start = n * 3 / 8
        min_stop = n - scale * 4
    ind_min = y[min_start:min_stop].argmin() + min_start

    # Now track to the side, waiting for the slope to change.
    if (slope > 0):
        start = ind_min + scale * 2
        stop = n
        step = 1
    else:
        start = ind_min - 2 * scale
        stop = -1
        step = -1
          
    idx = arange(start,stop,step)
    slope_change = (dy * slope < 0)[idx].nonzero()[0]
    if len(slope_change)==0:
        ind_max = stop - step
    else:
        ind_max = idx[slope_change.min()]

    # Return left and right sides of target range
    return min(ind_max, ind_min), max(ind_max, ind_min)


class SARamp(util.RCData):
    def __init__(self, filename=None, reduce_rows=True, tuning=None):
        util.RCData.__init__(self)
        self.data = None
        self.analysis = None
        self.tuning = tuning
        if filename != None:
            self.read_data(filename, reduce_rows=reduce_rows)

    @staticmethod
    def join(args):
        """
        Arguments are SARamp objects, loaded with data.
        """
        synth = SARamp()
        # Borrow most things from the first argument
        synth.mcefile = None
        synth.tuning = args[0].tuning
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
            raise RuntimeError, 'SARamp needs data.'
        if simple and self.gridded:
            raise RuntimeError, 'Simple SARamp expected (use split?)'

    def _check_analysis(self, existence=False):
        if self.analysis == None:
            if existence:
                self.analysis = {}
            else:
                raise RuntimeError, 'SARamp lacks desired analysis structure.'

    def reduce_rows(self):
        s = list(self.data_shape)
        n_r, n_c, n_fb = s[-3:]
        self.data.shape = (-1, n_r, n_c, n_fb)
        self.data = self.data.astype('float').mean(axis=-3).reshape(-1, n_fb)
        s[-3] = 1
        self.data_shape = s
        self.rows = [-1]

    def from_array(self, data, shape=None, fb=None, origin='array'):
        """
        Load SA data from an array, for testing or whatever.
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
            self.bias = 0 # ?
        else:
            self.bias_style = 'select'
            self.bias = [0 for i in range(n_col)]

    def read_data(self, filename, reduce_rows=True):
        self.mcefile = MCEFile(filename)
        self.data = self.mcefile.Read(row_col=True).data
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}
        self.gridded = True
        self.data_shape = self.data.shape
        # Ravel row/col dimension
        self.data.shape = (-1, self.data.shape[-1])
        # Record the rows and columns, roughly
        rf = self.mcefile.runfile
        rcs = rf.Item('FRAMEACQ', 'RC', type='int')
        self.cols = array([i+(rc-1)*8 for rc in rcs for i in range(8)]).ravel()
        self.rows = array([i for i in arange(self.data_shape[0])])

        # Might easily include a bias ramp.
        bias_ramp = (rf.Item('par_ramp', 'par_title loop1 par1', \
                                 array=False).strip() == 'sa_bias')
        if bias_ramp:
            bias0, d_bias, n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
            self.bias_style = 'ramp'
            self.bias = bias0 + d_bias*arange(n_bias)
        else:
            # If we weren't ramping the SA bias, we like to know what it was.
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            self.bias_style = 'select'
            self.bias = array(rf.Item('HEADER', 'RB sa bias', type='int'))[self.cols]

        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb

        # Natural order
        if bias_ramp:
            self.data.shape = (len(self.rows), len(self.cols), n_bias, n_fb)
            self.data = self.data.transpose([2, 0, 1, 3])
            self.data_shape = self.data.shape
        self.data = self.data.reshape(-1, n_fb)
        if reduce_rows:
            self.reduce_rows()
        
    def split(self):
        """
        Split multi-bias data (from combined bias+fb ramp) into single
        objects per bias.  Returns a list of single bias ramps.
        """
        if self.bias_style == 'select':
            return [self]

        n_bias, n_row, n_col, n_fb = self.data_shape
        copy_keys = ['data_origin', 'rows', 'cols', 'fb', 'd_fb', 'tuning', 'mcefile']
        output = []
        for i in range(n_bias):
            sa = SARamp()
            for k in copy_keys:
                setattr(sa, k, getattr(self, k))
            sa.data = self.data.reshape(n_bias, -1)[i].reshape(-1, n_fb)
            sa.data_shape = self.data_shape[1:]
            sa.gridded = True
            sa.bias_style = 'select'
            sa.bias = [self.bias[i] for c in self.cols]
            output.append(sa)
        return output

    def subselect(self, selector=None):
        """
        Reduce the SA data by selecting certain curves from
        super-entries in each column.
        """
        if selector == None:
            self._check_analysis()
            selector = self.analysis['y_span_select']
        sa = self.split()[0]
        sa.bias_style = 'select'
        sa.data.shape = sa.data_shape
        self.data.shape = self.data_shape
        for i, s in enumerate(selector):
            sa.bias[i] = self.bias[s]
            sa.data[:,i,:] = self.data[s,:,i,:]
        sa.data.shape = (-1, sa.data_shape[-1])
        self.data.shape = (-1, self.data_shape[-1])
        return sa

    def reduce(self, slope=None):
        self.reduce1()
        self.reduce2(slope=slope)
        return self.analysis

    def reduce1(self):
        """
        Compute peak-to-peak response.
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
        self._check_data()
        self._check_analysis(existence=True)

        # Convert to 1 slope per column
        if slope == None:
            slope = sign(self.tuning.get_exp_param('sq2_servo_gain')[self.cols])
        if not hasattr(slope, '__getitem__'):
            slope = array([slope]*len(self.cols))
        
        # Smooth SA data; use kernel with odd width or the lag is non-integral.
        n_fb = len(self.fb)
        scale = max([8 * n_fb / 800, 0])
        y = servo.smooth(self.data, scale*2+1)

        # Analyze all SA curves for lock-points
        an = servo.get_lock_points(y, start=0, slope=slope)

        # Add feedback keys, with shift to counteract smoothing
        for k in ['lock', 'left', 'right']:
            an[k+'_x'] = self.fb[an[k+'_idx'] + scale]

        # Sub-sample to nearest integer feedback, rescale slopes based on d_fb
        an['lock_x'] += float(self.d_fb) * an['lock_didx']
        an['lock_slope'] /= self.d_fb

        self.analysis.update(an)
        return self.analysis

    def plot(self, plot_file=None):
        self._check_data()
        self._check_analysis()

        if self.bias_style != 'select':
            raise RuntimeError, 'We cannot plot whole ramps, just the final selection.'
        
        if plot_file == None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))
        # Plot plot plot
        return servo.plot(
            self.fb, self.data, self.data_shape[-3:-1],
            self.analysis, plot_file,
            shape=(4, 2),
            slopes=True,
            title=self.data_origin['basename'],
            titles=['Column %i - SA_bias=%6i' %(c,b) \
                    for c,b in zip(self.cols, self.bias)],
            xlabel='SA FB / 1000',
            ylabel='AD Units / 1000')

