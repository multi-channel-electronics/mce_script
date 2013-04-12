import os, time
import auto_setup.util as util
from numpy import *
from mce_data import MCERunfile, MCEFile

import servo

def go(tuning, rc, filename=None, fb=None, slope=None, bias=None, gain=None,
       do_analysis=True):

    ok, servo_data = acquire(tuning, rc, filename=filename, fb=fb,
                             bias=bias, gain=gain)
    if not ok:
        raise RuntimeError, servo_data['error']

    if not do_analysis:
        return None

    sq = SQ2Servo(servo_data['filename'], tuning=tuning)
    lock_points = sq.reduce(slope=slope)
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])

    # Return analysis
    return lock_points


def acquire(tuning, rc, filename=None, fb=None,
            bias=None, gain=None, old_servo=False):

    # File defaults
    if filename == None:
        filename, acq_id = tuning.filename(rc=rc, action='sq2servo')
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    if old_servo:
        # Biasing semantics are complicated, fix me.
        if bias == None:
            bias = tuning.get_exp_param('sq2_servo_bias_ramp')
        change_bias = not (bias == False)

        if (bias == True):
            bias = {}
            for k in ['start','count','step']:
                bias[k] = tuning.get_exp_param('sq2_servo_bias_%s'%k)
        elif (bias == False):
            bias = {'start': 0, 'count': 1, 'step': 0 }

        # FB
        if fb == None:
            fb = {}
            for k in ['start','count','step']:
                fb[k] = tuning.get_exp_param('sq2_servo_flux_%s'%k)
        if gain == None:
            if rc == 's':
                rci = 0
            else:
                rci = int(rc) - 1
            gain = tuning.get_exp_param('sq2_servo_gain')[rci*8]
    
        # Execute C servo program
        cmd = [os.path.join(tuning.bin_path, 'sq2servo'), '-E0', filename,
               bias['start'], bias['step'], bias['count'],
               fb['start'], fb['step'], fb['count'],
               rc, int(change_bias), gain, int(not change_bias)]
    else:
        cmd = [os.path.join(tuning.bin_path, 'sq2servo'), '-p', 50, '-E1', rc, filename]
        
    status = tuning.run(cmd)
    if status != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.base_dir, filename)
    rf = MCERunfile(fullname + ".run")
    n_frames = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2] * \
        rf.Item('par_ramp', 'par_step loop2 par1', type='int')[2]
    
    tuning.register(acq_id, 'tune_servo', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename': fullname }

class SQ2Servo(servo.SquidData):
    """
    Read and analyze SQ2 servo data.
    """
    # Note most useful behaviour is inherited from SquidData.
    stage_name = 'SQ2Servo'
    xlabel = 'SQ2 FB / 1000'
    ylabels = {'data': 'SA FB / 1000',
               'error': 'Error / 1000'}

    def __init__(self, filename=None, tuning=None):
        servo.SquidData.__init__(self, tuning=tuning)
        self.data_attrs.append('error')
        if filename != None:
            self.read_data(filename)

    def read_data(self, filename, reduce_rows=False):
        self.mcefile = None
        rf = MCERunfile(filename+'.run')
        self.rf = rf
        self.error, self.data = util.load_bias_file(filename+'.bias')

        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}
        self.gridded = True
        self.data_shape = self.data.shape
        # Ravel.
        self.data.shape = (-1, self.data.shape[-1])
        # Record the rows and columns, roughly
        rcs = rf.Item('FRAMEACQ', 'RC', type='int')
        self.cols = array([i+(rc-1)*8 for rc in rcs for i in range(8)]).ravel()
        self.rows = array([-1])

        # Fix me: runfile always indicates bias was ramped, even though it usually wasn't
        bias_ramp = (rf.Item('par_ramp', 'par_title loop1 par1', \
                                 array=False).strip() == 'sq2bias')
        if bias_ramp:
            bias0, d_bias, n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
            self.bias_style = 'ramp'
            self.bias = bias0 + d_bias*arange(n_bias)
        else:
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            n_bias = 1
        # This should just extend the else; the second clause is a bug work-around
        if not bias_ramp or (bias_ramp and n_bias == 1):
            self.bias_style = 'select'
            self.bias = array(rf.Item('HEADER', 'RB sq2 bias', type='int'))[self.cols]

        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb

        # Natural order
        if bias_ramp:
            self.data.shape = (len(self.rows), len(self.cols), n_bias, n_fb)
            self.data = self.data.transpose([2, 0, 1, 3])
        self.data_shape = self.data.shape
        self.data = self.data.reshape(-1, n_fb)
        self.error = self.error.reshape(-1, n_fb)

    def reduce(self, slope=None, lock_amp=True, x_adjust=None):
        self.reduce1()
        self.reduce2(slope=slope, lock_amp=lock_amp, x_adjust=x_adjust)
        return self.analysis

    def reduce2(self, slope=None, lock_amp=True, x_adjust=None):
        """
        Special reduction steps for SQ2 servo.
        """
        self._check_data()
        self._check_analysis(existence=True)
        
        if slope == None:
            slope = -sign(self.tuning.get_exp_param('sq1_servo_gain')*
                          self.tuning.get_exp_param('sq2_servo_gain'))
            slope = array(slope[self.cols])
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
            x_adjust = self.tuning.get_exp_param('sq2_servo_sq2fb_adjust',
                                                 default=0)
            if hasattr(x_adjust, '__getitem__'):
                x_adjust = x_adjust[self.cols]

        n_fb = len(self.fb)
        an = servo.get_lock_points(self.data, scale=n_fb/40,
                                   lock_amp=lock_amp, slope=slope,
                                   x_adjust=x_adjust/self.d_fb)
        # Add feedback keys
        for k in ['lock', 'left', 'right']:
            an[k+'_x'] = self.fb[an[k+'_idx']]

        # Tweak feedback values and rescale slopes
        d_fb = self.fb[1] - self.fb[0]
        an['lock_x'] += (d_fb * an['lock_didx']).astype('int')
        an['lock_slope'] /= d_fb

        self.analysis = an
        return an

    def plot_error(self, *args, **kwargs):
        if not 'data_attr' in kwargs:
            kwargs['data_attr'] = 'error'
        if not 'plot_file' in kwargs:
            kwargs['plot_file'] = os.path.join(self.tuning.plot_dir, '%s' % \
                                  (self.data_origin['basename'] + '_err'))
        return self.plot(*args, **kwargs)

    def ramp_summary(self):
        """
        If this is an analyzed bias ramp, returns a RampSummary loaded
        with the amplitudes, max and min values, and bias set points.
        """
        rs = SQ2ServoSummary.from_biases(self)
        rs.add_data('y_span', self.analysis['y_span'],
                    ylabel='Amplitude (/1000)')
        rs.add_data('y_max', self.analysis['y_max'],
                    ylabel='Max error (/1000)')
        rs.add_data('y_min', self.analysis['y_min'],
                    ylabel='Min error (/1000)')
        # Turn bias indices into biases; store as analysis.
        idx = self.analysis['y_span_select']
        rs.analysis = {'lock_x': self.bias[idx]}
        return rs


class SQ2ServoSummary(servo.RampSummary):
    xlabel = 'SQ2 BIAS'
