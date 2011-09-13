import numpy as np
from mce import mce

MCE_CHANS = 8

class mce_control(mce):
    def __init__(self, do_init=True, *args, **kwargs):
        mce.__init__(self, *args, **kwargs)
        if do_init:
            self.init()

    def init(self):
        self.n_rc = len(self.read('rca', 'fw_rev'))
        self.n_row = 41 # Fix me
        self.n_chan = 8 # Fix me?
        self.n_col = self.n_chan * self.n_rc
        # The col_map might need tweaking depending on what rcs are present.
        self.col_map = range(self.n_rc*MCE_CHANS)
        self.rc_list = ['rc%i'%(i+1) for i in range(self.n_rc)]

    """
    Data acquisition, numpified.
    """

    def read_data(self, count=None, data_only=True):
        _count = count
        if _count == None: _count = 1
        data = np.array(self.read_frames(_count, data_only=data_only))
        if count ==None:
            data.shape = (self.n_row, self.n_col)
        else:
            data.shape = (-1, self.n_row, self.n_col)
        return data

    def read_row(self, n=1, avg=False):
        d = np.array(self.read_frames(n, data_only=True))[:,:self.n_rc*MCE_CHANS]
        if avg:
            return d.mean(axis=0)
        return d

    """
    Read /write assistance.
    """

    def write_columns(self, param, data):
        # Duplicate values across all rows in each column parameter
        for c, d in enumerate(data):
            rc, chan = c/MCE_CHANS + 1, c%MCE_CHANS
            self.write('rc%i'%rc, param+'%i' % chan, [int(d)]*41)

    def io_rc_array_2d(self, param_fmt, data=None):
        """
        Read or write a parameter that is specified for each row and column,
        spread accross all readout cards.
        """
        if data == None:
            # read
            data = []
            for rc in self.rc_list:
                data += [self.read(rc, param_fmt%c) for c in range(self.n_chan)]
            return np.array(data)
        else:
            for i,rc in enumerate(self.rc_list):
                for c in range(self.n_chan):
                    self.write(rc, param_fmt%c, data[i*self.n_chan+c])
                    
    def io_rc_array_1d(self, param, data=None):
        if data == None:
            data = []
            for rc in self.rc_list:
                data += self.read(rc, param)
            return np.array(data)
        else:
            for i,rc in enumerate(self.rc_list):
                self.write(rc, param, data[i*self.n_chan:(i+1)*self.n_chan])

    """
    Sampling parameters.
    """

    def data_mode(self, mode=None):
        if mode == None:
            return self.read('rca', 'data_mode')[0]
        else:
            self.write('rca', 'data_mode', [mode])

    """
    Servo loop control.
    """

    def flux_quanta(self, n):
        self.write_columns('flx_quanta', [n]*(self.n_rc*MCE_CHANS))

    def flux_jumping(self, mode=None):
        if mode == None:
            return self.read('rca', 'en_fb_jump')[0]
        self.write('rca', 'en_fb_jump', [mode])

    def init_servo(self):
        self.write('rca', 'flx_lp_init', [1])

    def servo_mode(self, mode=None):
        if mode == None:
            return self.read('rca', 'servo_mode')[0]
        else:
            self.write('rca', 'servo_mode', [mode]*MCE_CHANS)
    
    """
    Convenient computations.
    """

    def dt(self):
        nr, dr, rl = [self.read('cc', k)[0] for k in 
                      ['num_rows', 'data_rate', 'row_len']]
        return float(nr * dr * rl) / 5e7

