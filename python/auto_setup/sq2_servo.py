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
        cmd = [os.path.join(tuning.bin_path, 'sq2servo'), '-E1', rc, filename]
        
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

class SQ2Servo(util.RCData):
    def __init__(self, filename=None, tuning=None):
        util.RCData.__init__(self)
        self.data = None
        self.analysis = None
        self.tuning = tuning
        if filename != None:
            self.read_data(filename)

    @staticmethod
    def join(args):
        """
        Arguments are SQ2Servo objects, loaded with data.
        """
        synth = SQ2Servo()
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
            raise RuntimeError, 'SQ2Servo needs data.'
        if simple and self.gridded:
            raise RuntimeError, 'Simple SQ2Servo expected (use split?)'

    def _check_analysis(self, existence=False):
        if self.analysis == None:
            if existence:
                self.analysis = {}
            else:
                raise RuntimeError, 'SQ2Servo lacks desired analysis structure.'

    def read_data(self, filename, reduce_rows=False):
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
        self.cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()
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
            # If we weren't ramping the SQ2 bias, we like to know what it was.
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            self.bias_style = 'select'
            self.bias = array(rf.Item('HEADER', 'RB sq2 bias', 'int'))[self.cols]

        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb

        # Natural order
        if bias_ramp:
            self.data.shape = (len(self.rows), len(self.cols), n_bias, n_fb)
            self.data = self.data.transpose([2, 0, 1, 3])
        self.data_shape = self.data.shape
        self.data = self.data.reshape(-1, n_fb)

    def split(self):
        """
        Split multi-bias data (from combined bias+fb ramp) into single
        objects per bias.  Returns a list of single bias servos.
        """
        if self.bias_style == 'select':
            return [self]

        n_bias, n_row, n_col, n_fb = self.data_shape
        copy_keys = ['data_origin', 'rows', 'cols', 'fb', 'd_fb']
        output = []
        for i in range(n_bias):
            sa = SQ2Servo()
            for k in copy_keys:
                exec('sa.%s = self.%s' %(k,k))
            sa.data = self.data.reshape(n_bias, -1)[i].reshape(-1, n_fb)
            sa.data_shape = self.data_shape[1:]
            sa.bias_style = 'select'
            sa.bias = [self.bias[i] for c in self.cols]
            output.append(sa)
        return output

    def reduce(self, slope=None):
        self._check_data()
        self._check_analysis(existence=True)
        
        if slope == None:
            slope = self.tuning.get_exp_param('sq2_servo_gain')
        if not hasattr(slope, '__getitem__'): slope = [slope]*(max(self.cols)+1)
        slope = array(slope)[self.cols]

        if any(slope != slope[0]):
            z = zeros(self.data_shape[:-1])
            z[:,:,:] = slope.reshape(1,-1,1)
            slope = z
        else:
            slope = slope[0]
        n_fb = len(self.fb)
        self.analysis = servo.get_lock_points(self.data, scale=n_fb/40, yscale=4000, lock_amp=True, slope=slope)

        # Add feedback keys
        for k in ['lock', 'left', 'right']:
            self.analysis[k+'_x'] = self.fb[self.analysis[k+'_idx']]
        return self.analysis
        
    def plot(self, plot_file=None):
        self._check_data()
        self._check_analysis()

        if plot_file == None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))

        # Plot plot plot
        return servo.plot(
            self.fb, self.data, self.data_shape[-3:-1], self.analysis,
            plot_file,
            title=self.data_origin['basename'],
            titles=['Column %i' %c for c in self.cols],
            xlabel='SQ2 FB / 1000',
            ylabel='SA FB / 1000')
