import time, os, glob
import auto_setup.util as util
from numpy import *
from mce_data import MCERunfile, MCEFile

import servo

def go(tuning, rc, filename=None, fb=None, slope=None, gain=None):

    super_servo = tuning.get_exp_param('config_fast_sq2') or \
        tuning.get_exp_param('sq1_servo_all_rows')

    if not super_servo:
        f = open(os.path.join(tuning.base_dir, "row.init"), "w")
        for r in tuning.get_exp_param('sq2_rows'):
            f.write("%i\n" % r)
        f.close()
        f = open(os.path.join(tuning.base_dir, "sq2fb.init"), "w")
        for x in tuning.get_exp_param('sq2_fb'):
            f.write("%i\n" % x)
        f.close()

    ok, servo_data = acquire(tuning, rc, filename=filename, fb=fb,
                             gain=gain, super_servo=super_servo)
    if not ok:
        raise RuntimeError, servo_data['error']

    sq = SQ1Servo(servo_data['filename'], tuning=tuning)
    lock_points = sq.reduce()
    plot_out = sq.plot()
    tuning.register_plots(*plot_out['plot_files'])

    # Return dictionary of relevant results
    lock_points['super_servo'] = super_servo
    lock_points['data_shape'] = sq.data_shape
    lock_points['cols'] = sq.cols
    return lock_points


def acquire(tuning, rc, filename=None, fb=None,
            gain=None, super_servo=False, old_servo=False):

    # File defaults
    if filename == None:
        filename, acq_id = tuning.filename(rc=rc, action='sq1servo')
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    if super_servo:
        cmd = [tuning.bin_path+'sq1servo_all', '-p', 50]
    else:
        cmd = [tuning.bin_path+'sq1servo']

    if old_servo:
        # FB
        if fb == None:
            fb = {}
            for k in ['start','count','step']:
                fb[k] = tuning.get_exp_param('sq1_servo_flux_%s'%k)
        if gain == None:
            if rc == 's':
                rci = 0
            else:
                rci = int(rc) - 1
            gain = tuning.get_exp_param('sq1_servo_gain')[rci*8]
    
        # This syntax is for pre-2010 servo programs that only do one gain.
        cmd += ['-E0', filename, 0,0,0,
                fb['start'], fb['step'], fb['count'],
                rc, 0, tuning.get_exp_param("default_num_rows"), gain, 1]
    else:
        cmd += ['-p', 50, '-E1', rc, filename]

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


class SQ1Servo(util.RCData):
    def __init__(self, filename=None, tuning=None):
        util.RCData.__init__(self, data_attrs=['data', 'error'])
        self.data = None
        self.analysis = None
        self.tuning = tuning
        if filename != None:
            self.read_data(filename)

    @staticmethod
    def join(args):
        """
        Arguments are SQ1Servo objects, loaded with data.
        """
        synth = SQ1Servo()
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
            raise RuntimeError, 'SQ1Servo needs data.'
        if simple and self.gridded:
            raise RuntimeError, 'Simple SQ1Servo expected (use split?)'

    def _check_analysis(self, existence=False):
        if self.analysis == None:
            if existence:
                self.analysis = {}
            else:
                raise RuntimeError, 'SQ1Servo lacks desired analysis structure.'

    def _read_super(self, filename):
        """
        Helper for read_data that assembles array of data from all-row
        sq1servo .bias files.
        """
        data = []
        for n_row in range(64):
            f = '%s.r%02i.bias' % (filename, n_row)
            if not os.path.lexists(f):
                break
            data.append(util.load_bias_file(f))
        self.gridded = True
        self.error = array([a for a,_ in data])
        self.data = array([a for _,a in data])
        self.rows = array([i for i in range(n_row)])
        n_bias, _, n_col, n_fb = self.data_shape
        self.data = self.data.reshape(n_row*n_col,n_bias,n_fb). \
            transpose([1,0,2]).reshape(-1, n_fb)
        self.error = self.error.reshape(n_row*n_col,n_bias,n_fb). \
            transpose([1,0,2]).reshape(-1, n_fb)
        self.data_shape = n_bias, n_row, n_col, n_fb

    def _read_single(self, filename):
        """
        Helper for read_data that loads a single-row sq1servo file.
        """
        self.error, self.data = util.load_bias_file(filename+'.bias')
        # Awkward indexing...
        col_idx = self.cols - (amin(self.cols) / 8)*8
        self.rows = array(self.rf.Item('servo_init', 'row.init', type='int'))[col_idx]
        n_row = 1
        self.gridded = False
        n_bias, _, n_col, n_fb = self.data_shape
        self.data = self.data.reshape(n_row*n_col,n_bias,n_fb). \
            transpose([1,0,2]).reshape(-1, n_fb)
        self.error = self.error.reshape(n_row*n_col,n_bias,n_fb). \
            transpose([1,0,2]).reshape(-1, n_fb)

    def read_data(self, filename):
        """
        Loads an sq1servo data set.  Can probably figure out if there is
        multi-row data present and do The Right Thing.
        """
        rf = MCERunfile(filename+'.run')
        self.rf = rf
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}
        # Record the columns
        rcs = rf.Item('FRAMEACQ', 'RC', type='int')
        self.cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()

        # Fix me: runfile always indicates bias was ramped, even though it usually wasn't
        bias_ramp = (rf.Item('par_ramp', 'par_title loop1 par1', \
                                 array=False).strip() == 'sq1bias')
        if bias_ramp:
            bias0, d_bias, n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
            self.bias_style = 'ramp'
            self.bias = bias0 + d_bias*arange(n_bias)
        else:
            # If we weren't ramping the SQ1 bias, we like to know what it was.
            fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
            self.bias_style = 'select'
            self.bias = array(rf.Item('HEADER', 'RB sq2 bias', 'int'))[self.cols]
            n_bias = 1

        self.d_fb = d_fb
        self.fb = fb0 + arange(n_fb) * d_fb

        # Prime
        self.data_shape = (n_bias, 1, len(self.cols), n_fb)

        # Attempt load after counting bias/fb steps
        if len(glob.glob(filename+'.bias')):
            self._read_single(filename)
        else:
            self._read_super(filename)

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
            sa = SQ1Servo()
            for k in copy_keys:
                exec('sa.%s = self.%s' %(k,k))
            sa.data = self.data.reshape(n_bias, -1)[i].reshape(-1, n_fb)
            sa.data_shape = self.data_shape[1:]
            sa.gridded = self.gridded
            sa.bias_style = 'select'
            sa.bias = [self.bias[i] for c in self.cols]
            output.append(sa)
        return output

    def reduce(self, slope=1.):
        self._check_data()
        self._check_analysis(existence=True)
        
        if slope == None:
            slope = self.tuning.get_exp_param('sq2servo_gain')
        if not hasattr(slope, '__getitem__'): slope = [slope]*4
        if len(slope) < 8:
            slope = (zeros((8,len(slope))) + slope).ravel()
        slope = slope[self.cols]

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
            self.fb, self.data, self.data_shape[-3:-1],
                   self.analysis, plot_file,
                   title=self.data_origin['basename'],
                   xlabel='SQ1 FB / 1000',
                   ylabel='SQ2 FB / 1000',
                   set_points=True)

