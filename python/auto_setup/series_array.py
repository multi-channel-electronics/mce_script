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


class SARamp(servo.SquidData):
    """
    Read and analyze SA ramp data.
    """
    # Note most useful behaviour is inherited from SquidData.
    stage_name = 'SARamp'
    xlabel='SA FB / 1000'
    ylabels= {'data': 'AD Units / 1000'}

    def __init__(self, filename=None, reduce_rows=True, tuning=None):
        servo.SquidData.__init__(self, tuning=tuning)
        if filename != None:
            self.read_data(filename, reduce_rows=reduce_rows)

    def read_data(self, filename, reduce_rows=True):
        self.mcefile = MCEFile(filename)
        self.rf = self.mcefile.runfile
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

    def reduce(self, slope=None):
        self.reduce1()
        self.reduce2(slope=slope)
        return self.analysis

    def reduce2(self, slope=None, x_adjust=None):
        """
        Special analysis steps for SA ramp.
        """
        self._check_data()
        self._check_analysis(existence=True)

        # Convert to 1 slope per column
        if slope == None:
            slope = -sign(self.tuning.get_exp_param('sq2_servo_gain')[self.cols])
        if not hasattr(slope, '__getitem__'):
            slope = array([slope]*len(self.cols))
        
        # Make slope either a scalar, or 1 value per curve.
        if any(slope != slope[0]):
            z = zeros(self.data.shape[:-1])
            z[...,:] = slope.reshape(1,-1)
            slope = z
        else:
            slope = slope[0]

        if x_adjust == None:
            x_adjust = self.tuning.get_exp_param('sa_ramp_safb_adjust',
                                                 default=0)
            if hasattr(x_adjust, '__getitem__'):
                x_adjust = x_adjust[self.cols]

        # Smooth SA data; use kernel with odd width or the lag is non-integral.
        n_fb = len(self.fb)
        scale = max([8 * n_fb / 800, 0])
        y = servo.smooth(self.data, scale*2+1)

        # Analyze all SA curves for lock-points
        an = servo.get_lock_points(y, start=0, slope=slope,
                                   x_adjust=x_adjust/self.d_fb)

        # Add feedback keys, with shift to counteract smoothing
        for k in ['lock', 'left', 'right']:
            an[k+'_x'] = self.fb[an[k+'_idx'] + scale]

        # Sub-sample to nearest integer feedback, rescale slopes based on d_fb
        an['lock_x'] += float(self.d_fb) * an['lock_didx']
        an['lock_slope'] /= self.d_fb

        self.analysis.update(an)
        return self.analysis

    def ramp_summary(self):
        """
        If this is an analyzed bias ramp, returns a RampSummary loaded
        with the amplitudes, max and min values, and bias set points.
        """
        rs = SARampSummary.from_biases(self)
        rs.add_data('y_span', self.analysis['y_span'],
                    ylabel='Amplitude (/1000)')
        rs.add_data('y_max', self.analysis['y_max'],
                    ylabel='Max error (/1000)')
        rs.add_data('y_min', self.analysis['y_min'],
                    ylabel='Min error (/1000)')
        # Turn bias indices into biases; store as analysis.
        idx = self.analysis['select_col_sel']
        rs.analysis = {'lock_x': self.bias[idx]}
        return rs


class SARampSummary(servo.RampSummary):
    xlabel = 'SA BIAS'

