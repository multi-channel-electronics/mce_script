import numpy as np

try:
    # Way of the future
    import pymce
    from pymce import MCE as mce
except:
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
        self.n_chan = MCE_CHANS # Fix me?
        self.n_col = self.n_chan * self.n_rc
        # The col_map might need tweaking depending on what rcs are present.
        self.col_map = range(self.n_rc*self.n_chan)
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

    def read_row(self, n=None, avg=False):
        _n = n
        if _n == None:
            _n = 1
        d = np.array(self.read_frames(_n, data_only=True))[:,:self.n_rc*MCE_CHANS]
        if n==None:
            return d[0]
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

    def io_readwrite(self, card, param, data=None):
        if data == None:
            return np.array(self.read(card, param))
        else:
            return self.write(card, param, data)

    def io_rc_sync(self, param, data=None):
        """
        Read/write a "synced" parameter from/to all RCs.  This kind of
        parameter should be the same accross all RCs; e.g. data_mode,
        sample_num.  Writes/returns a single value (even if each RC
        returns a vector of values).
        """
        if data == None:
            vals = np.array(self.read('rca', param))
            if not np.all(vals==vals[0]):
                print '(Warning: inconsistent data for "%s" across RCs.)' % \
                    param
            return vals[0]
        else:
            self.write('rca', param, data)

    def io_rc_array_2d(self, param_fmt, data=None):
        """
        Read or write a parameter that is specified for each row and
        column, spread accross all readout cards.  param_fmt should
        accept an integer representing the column on the readoutcard; e.g.
        
              adc_offset%i
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
        """
        Read or write a parameter that is specified for each column,
        but is spread accross all readout cards.  This is uncommon,
        since these tend to have aliases already, such as "sq1
        fb_const".        
        """
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
        return self.io_rc_sync('data_mode', mode)
        if mode == None:
            return self.read('rca', 'data_mode')[0]
        else:
            self.write('rca', 'data_mode', [mode])

    def sample_num(self, num=None):
        return self.io_rc_sync('sample_num', num)

    def sample_delay(self, num=None):
        return self.io_rc_sync('sample_dly', num)

    """
    Servo loop control.
    """

    def init_servo(self):
        return self.io_rc_syn('flx_lp_init', [1])

    def servo_mode(self, mode=None):
        if mode != None:
            # Broadcast to all columns
            mode = [mode] * MCE_CHANS
        return self.io_rc_sync('servo_mode', mode)

    def gaini(self, gains=None):
        return self.io_rc_array_2d('gaini%i', gains)
    
    def flux_quanta(self, quanta=None):
        return self.io_rc_array_2d('flx_quanta%i', quanta)

    def flux_jumping(self, mode=None):
        return self.io_rc_syn('en_fb_jump')

    def fb_const(self, fb=None):
        return self.io_readwrite('sq1', 'fb_const', fb)


    """
    Convenient computations.
    """

    def dt(self):
        nr, dr, rl = [self.read('cc', k)[0] for k in 
                      ['num_rows', 'data_rate', 'row_len']]
        return float(nr * dr * rl) / 5e7

