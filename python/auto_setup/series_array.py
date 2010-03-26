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

    sa = SARamp(ramp_data['filename'])
    lock_points = sa.reduce(tuning=tuning)
    sa.plot(tuning=tuning)

    # Return dictionary of relevant results
    return {'sa_bias': lock_points['sa_bias'],
            'fb': lock_points['lock_x'],
            'target': lock_points['lock_y'],
            }

def acquire(tuning, rc, filename=None, do_bias=None):
    # Convert to 0-based rc indices.
    rci = rc - 1

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

class SARamp:
    def __init__(self, filename=None, reduce_rows=False):
        self.data = None
        self.analysis = None
        if filename != None:
            self.read_data(filename, reduce_rows=reduce_rows)

    def _check_data(self, simple=False):
        if self.data == None:
            raise RuntimeError, 'SARamp needs data.'
        if simple and self.data_style != 'rectangle':
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

    def read_data(self, filename, reduce_rows=False):
        self.mcefile = MCEFile(filename)
        self.data = self.mcefile.Read(row_col=True).data
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}
        self.data_style = 'rectangle'
        self.data_shape = self.data.shape
        # Ravel.
        self.data.shape = (-1, self.data.shape[-1])
        # Record the rows and columns, roughly
        rf = self.mcefile.runfile
        rcs = rf.Item('FRAMEACQ', 'RC', type='int')
        self.cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()
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
            self.bias = array(rf.Item('HEADER', 'RB sa bias', 'int'))[self.cols]

        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb

        # Natural order
        if bias_ramp:
            self.data.shape = (len(self.rows), len(self.cols), n_bias, n_fb)
            self.data = self.data.transpose([2, 0, 1, 3])
            self.data_shape = self.data.shape
            self.data_style = 'super-rectangle'
        else:
            self.data_shape = self.data.shape
            self.data_style = 'rectangle'
        self.data = self.data.reshape(-1, n_fb)
        if reduce_rows:
            self.reduce_rows()
        
    def split(self):
        """
        Split multi-bias data (from combined bias+fb ramp) into single
        objects per bias.  Returns a list of single bias ramps.
        """
        if self.data_style != 'super-rectangle':
            return [self]

        n_bias, n_row, n_col, n_fb = self.data_shape
        copy_keys = ['data_origin', 'rows', 'cols', 'fb', 'd_fb', 'mcefile']
        output = []
        for i in range(n_bias):
            sa = SARamp()
            for k in copy_keys:
                exec('sa.%s = self.%s' %(k,k))
            sa.data = self.data.reshape(n_bias, -1)[i].reshape(-1, n_fb)
            sa.data_shape = self.data_shape[1:]
            sa.data_style = 'rectangle'
            sa.bias_style = 'select'
            sa.bias = [self.bias[i] for c in self.cols]
            output.append(sa)
        return output

    def subselect(self, selector):
        """
        Reduce the SA data by selecting certain curves from
        super-entries in each column.
        """
        self._check_analysis(existence=True)
        sa = self.split()[0]
        sa.data.shape = sa.data_shape
        self.data.shape = self.data_shape
        for i, s in enumerate(selector):
            sa.bias[i] = self.bias[s]
            sa.data[:,i,:] = self.data[s,:,i,:]
        sa.data.shape = (-1, sa.data_shape[-1])
        self.data.shape = (-1, self.data_shape[-1])
        return sa

    def reduce(self, tuning=None):
        self.reduce1()
        self.reduce2(tuning=tuning)
        return self.analysis

    def reduce1(self):
        """
        Compute peak-to-peak response.
        """
        self._check_data()
        self._check_analysis(existence=True)
        span = amax(self.data, axis=-1) - amin(self.data, axis=-1)
        self.analysis['y_span'] = span
        if self.data_style == 'super-rectangle':
            # Identify bias index of largest response in each column
            select = span.reshape(self.data_shape[:-1]).max(axis=-2).argmax(axis=0)
            self.analysis['y_span_select'] = select
        return self.analysis
    
    def reduce2(self, tuning=None, slope=None):
        self._check_data()
        self._check_analysis(existence=True)

        # Convert to 1 slope per column
        if slope == None:
            slope = tuning.get_exp_param('sq2_servo_gain')
        if not hasattr(slope, '__getitem__'): slope = [slope]*max(self.cols)
        slope = slope[self.cols]

        # Analyze all SA curves for lock-points
        n_fb = len(self.fb)
        scale = max([8 * n_fb / 400, 1])
        y = servo.smooth(self.data, scale)
        x_offset = scale/2
        dy = y[:,1:] - y[:,:-1]
        y = y[:,:-1]

        lock_idx, left_idx, right_idx = [], [], []
        for i, (yy, ddy) in enumerate(zip(y, dy)):
            s = slope[i % self.data_shape[-2]]
            # Find position of an SA minimum.  Search range depends on desired
            # locking slope because we will eventually need to find an SA max.
            if (s > 0):
                min_start = scale * 4
                min_stop = n_fb * 5 / 8
            else:
                min_start = n_fb * 3 / 8
                min_stop = n_fb - scale * 4

            ind_min = yy[min_start:min_stop].argmin() + min_start

            # Now track to the side, waiting for the slope to change.
            if (s > 0):
                start = ind_min + scale * 2
                stop = len(ddy)
                step = 1
            else:
                start = ind_min - 2 * scale
                stop = -1
                step = -1
          
            idx = arange(start,stop,step)
            slope_change = (ddy * s < 0)[idx].nonzero()[0]
            if len(slope_change)==0:
                ind_max = stop - step
            else:
                ind_max = idx[slope_change.min()]

            # Lock on half-way point between minimum and maximum
            lock_idx.append((ind_min+ind_max)/2)
            left_idx.append(min(ind_max,ind_min))
            right_idx.append(max(ind_max,ind_min))

        lock_y = array([int(yy[i]) for i,yy in zip(lock_idx, y)])
        for x in ['lock_idx', 'left_idx', 'right_idx']:
            self.analysis[x] = eval('array(%s)' % (x))
        self.analysis.update({
                'lock_y': lock_y,
                'slope': slope,
                })
        # Add feedback keys
        for k in ['lock', 'left', 'right']:
            self.analysis[k+'_x'] = self.fb[self.analysis[k+'_idx']]
        return self.analysis

    def plot(self, tuning=None, plot_file=None, format='pdf'):
        self._check_data()
        self._check_analysis()
        if plot_file == None:
            plot_file = os.path.join(tuning.plot_dir, '%s.%s' % \
                                         (self.data_origin['basename'], format))
        # Plot plot plot
        servo.plot(self.fb, self.data, self.data_shape[-3:-1],
                   self.analysis, plot_file,
                   title=self.data_origin['basename'],
                   titles=['Column %i - SA_bias=%6i' %(c,b) \
                               for c,b in zip(self.cols, self.bias)],
                   xlabel='SA FB / 1000',
                   ylabel='AD Units / 1000')

