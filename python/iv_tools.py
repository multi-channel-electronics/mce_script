import os

import subprocess as sp
import numpy as np

from mce_data import MCEFile, unwrap

from auto_setup import config

class runfile_block:
    """
    Write (especially) numpy arrays to a runfile-block file.
    """
    def __init__(self, filename, mode='w', data_cols=None):
        self.fout = open(filename, mode)
        self.data_cols = data_cols

    def __del__(self):
        self.close()

    def write_scalar(self, key, value, format='%s'):
        self.fout.write(('<%s> '+format+'\n') % (key, value))

    def write_vector(self, key, value, format='%.6f'):
        _value = ' '.join([format % x for x in value])
        self.write_scalar(key, _value)
    
    def write_array(self, key, value, format='%.6f'):
        data_cols = np.arange(value.shape[1])
        if self.data_cols != None:
            data_cols = self.data_cols
        for c in range(value.shape[1]):
            self.write_vector(key % data_cols[c], value[:,c], format)

    def close(self):
        if self.fout != None:
            self.fout.close()
        self.fout


class adict:
    """
    Just a holder for arrays.  Members of a particular types, but with
    the same shape are added with the "define" method.

    Set all member arrays, for some index, with a dictionary passed to
    add_item.
    """
    def __init__(self, keys=None, types=None, shape=None):
        self.keys = []
        if keys != None:
            self.define(keys, types, shape)
    def define(self, keys, types, shape):
        for k, t in zip(keys,types):
            setattr(self, k, np.zeros(shape, dtype=t))
            self.keys.append(k)
    def add_item(self, index, source):
        for k, v in source.iteritems():
            if k in self.keys:
                getattr(self,k)[index] = v

def read_ascii(filename, data_start=0, comment_chars=[]):
    data = []
    for line in open(filename):
        w = line.split()
        if len(w) == 0 or w[0][0] in comment_chars: continue
        data.append([float(x) for x in w])
    return np.transpose(data)


class IVData:
    """
    Container for the vectors pertaining to IV curves.  Raw data can
    be loaded from an MCE flatfile, or something.  Based on array
    configuration data (cables resistances and shunts and stuff), the
    bias and response in physical units can be computed.  Then using a
    branch decomposition (IVBranches class), parameters such as the
    normal resistance and bias power can be computed.  Once a bias
    point has been chosen, the quantities at the bias point can be
    computed.

    Calling sequence is probably:
     .read
     .compute_physical
     .compute_tes
     .get_setpoints
    """
    def __init__(self, filename=None, biasfile=None, runfile=True):
        if filename != None:
            self.read(filename, biasfile, runfile)

    def read(self, filename, biasfile=None, runfile=True):
        """
        Load IV feedback data; extract and unwrap it.  Load associated
        runfile and determine the bias values (in DAC units) applied.
        """
        self.mcefile = MCEFile(filename, runfile=runfile)
        self.runfile = self.mcefile.runfile
        self.mcedata = self.mcefile.Read(row_col=True,
                                         do_unwrap=True,
                                         unfilter='DC').data
        self.data_cols = np.array(self.mcefile._NameChannels(row_col=True)[1])
        # Also load the list of TES bias values... this has got to go.
        if biasfile == None:
            biasfile = filename + '.bias'
        self.bias_dac = read_ascii(biasfile, comment_chars=['<', '#'])[0]
        self.n_row, self.n_col, self.n_pts = self.mcedata.shape
        if self.bias_dac.shape[0] != self.n_pts:
            raise RuntimeError, 'weird .bias file'
    
    def compute_physical(self, ar_par):
        """
        Convert biases and feedbacks to physical units, using array
        parameters passed in through dictionary ar_par.
        """
        # Differentials
        ## TES bias DAC voltage, per DAC unit
        self.dbias_ddac = ar_par['bias_DAC_volts'] / 2**ar_par['bias_DAC_bits']
        R33, Rfb = 49.9, ar_par['Rfb_total']
        fb_DAC_volts = ar_par['fb_DAC_amps'] * Rfb * R33 / (R33 + Rfb)
        ## SQ1 FB DAC voltage, per DAC unit
        self.dfb_ddac = fb_DAC_volts / 2**ar_par['fb_DAC_bits']
        ## TES current, per unit FB DAC voltage
        self.di_dfb = 1 / (ar_par['M_ratio']*Rfb)

        ## Vectors
        self.bias_v = self.bias_dac * self.dbias_ddac
        self.fb_v = self.mcedata * \
            ar_par['fb_normalize'][self.data_cols].reshape(1,-1,1) * \
            self.dfb_ddac

    def compute_tes(self, iv_data, ar_par, Rshunt,
                    update_iv_data=True):
        """
        Use IVPartition results in iv_data and TESShunts data in
        Rshunt to compute all kinds of useful stuff about this TES load curve.
        """
        nr, nc = self.n_row, self.n_col
        ## Remove intercept of normal branch and compute true TES current.
        fb_v0 = iv_data.norm_offset.reshape((self.n_row,self.n_col,1))
        self.tes_i = 1e6 * self.di_dfb * (self.fb_v - fb_v0)
        ## Use shunt to get TES voltage
        Rb = ar_par['Rbias_arr_total'][ar_par['bias_lines'][self.data_cols]]
        self.tes_v = 1e6 * Rshunt.R.reshape(nr, nc,1) * \
            (self.bias_v.reshape(1,1,-1)/Rb.reshape(1,-1,1) - self.tes_i*1e-6)
        ## The resistance vector; just the ratio of voltage to current.
        self.tes_R = self.tes_v / self.tes_i
        ## The power
        self.tes_P = self.tes_v * self.tes_i
        ## More branch analysis...
        self.ok_rc = zip(*iv_data.ok.nonzero())
        if update_iv_data:
            ## Estimate R_normal from tes_R
            for r, c in self.ok_rc:
                i0, i1 = iv_data.norm_idx0[r,c], iv_data.norm_idx1[r,c]+1
                iv_data.R_norm[r,c] = self.tes_R[r,c,i0:i1].mean()
            ## Mark the transition index based on R drop.
            for r, c in self.ok_rc:
                i0, i1 = iv_data.norm_idx1[r,c], iv_data.super_idx0[r,c]
                trans = (self.tes_R[r,c,i0:i1] < 0.9*iv_data.R_norm[r,c]).nonzero()[0]
                if trans.shape[-1] > 0:
                    iv_data.trans_idx[r,c] = trans[0] + i0
            ## Saturation power, considering only points with R > .5 Rn
            for r, c in self.ok_rc:
                i0 = iv_data.super_idx0[r,c]
                norm_region = (self.tes_R[r,c,:i0] > 0.5*iv_data.R_norm[r,c]).\
                    nonzero()[0]
                if norm_region.shape[-1] == 0:
                    continue
                i0 = norm_region.max()
                iv_data.psat[r,c] = self.tes_P[r,c,i0]
        ## Curves of fraction of R_normal (formerly percent of R normal)
        self.tes_fracRn = self.tes_R / iv_data.R_norm.reshape((nr, nc, 1))
        ## Responsivity as function of bias, including FB sign correction.
        self.resp = self.di_dfb * self.dfb_ddac * 1e-6*self.tes_v * \
            (1 - Rshunt.R.reshape((nr, nc, 1))/self.tes_R) / \
            ar_par['fb_normalize'][self.data_cols].reshape(-1, 1)

    def get_setpoints(self, iv_data, target):
        setpoints = np.zeros(self.tes_fracRn.shape[:2], dtype='int')
        idx = iv_data.super_idx0
        for r, c in self.ok_rc:
            # eligible indices
            upper_region = (self.tes_fracRn[r,c,:idx[r,c]] > target).nonzero()[0]
            if upper_region.shape[-1] == 0:
                continue
            setpoints[r,c] = upper_region.max()
        return setpoints

        

class IVBranches(adict):
    def __init__(self, shape):
        keys = ['ok',
                'norm_offset', 'norm_idx0', 'norm_idx1', 'R_norm',
                'super_offset', 'super_idx0', 'super_idx1', 'R_super',
                'trans_idx',
                'psat',
                ]
        dtypes = ['bool',
                  'float', 'int', 'int', 'float',
                  'float', 'int', 'int', 'float',
                  'int',
                  'float',
                  ]
        adict.__init__(self, keys, dtypes, shape)
        self.n_row, self.n_col = shape
        
    def analyze_curves(self, filedata, rows=None, cols=None, **kwargs):
        ## Analyze only the requested rows and columns...
        if cols == None:
            cols = range(self.n_col)
        if rows == None:
            rows = range(self.n_row)
        for c in cols:
            for r in rows:
                det = analyze_IV_curve(filedata.bias_v, filedata.fb_v[r,c],
                                       **kwargs)
                self.add_item((r, c), det)
        

class TESShunts:
    def __init__(self, shape):
        self.R = np.zeros(shape, 'float')
        self.ok = np.zeros(shape, 'bool')

    @classmethod
    def from_srdp_files(cls, shape, filename_template, data_cols):
        self = cls(shape)
        for c in data_cols:
            sd = read_ascii(filename_template%c, comment_chars=['#'])
            rows, Rs = sd[0].astype('int'), sd[1]
            self.R[rows, c] = Rs
            self.ok[rows, c] = True
        return self

    @classmethod
    def for_act(cls, shape, filename_template, data_cols, ar_par,
                rshunt_bug=False):
        self = cls.from_srdp_files(shape, filename_template, data_cols)
        self.ok *= (ar_par['good_shunt_range'][0] < self.R) * \
            (self.R < ar_par['good_shunt_range'][1])
        # Sub in default value for bad entries.
        self.R[~self.ok] = ar_par['default_Rshunt']
        # Apply that bug?  Off by one row.
        if rshunt_bug:
            # This is just going to cause errors...
            Rshunt.R = Rshunt[:,n_col-1:]
        # AR3 exception
        if ar_par['array'] == 'AR3':
            self.R[(data_cols >= 24)*~shunts_ok] = 0.0007
        return self

class logger:
    def __init__(self, verbosity=0, indent=True):
        self.v = verbosity
        self.indent = indent
    def write(self, s, level=0):
        if level <= self.v:
            if self.indent:
                print ' '*level,
            print s
    def __call__(self, *args, **kwargs):
        return self.write(*args, **kwargs)

def load_array_params(filename=None, array_name=None):
    if array_name == None:
        array_name = open(os.path.join(mas_path().data_root(),
            'array_id')).readline().strip()
    if filename == None:
        filename = os.path.join(mas_path().config_dir(),
                'array_%s.cfg' % array_name)
    cfg = config.configFile(filename)
    cfg.update({'array': array_name,
                'source_file': filename})
    # Common post-processing
    ## Include cable resistance
    cfg['Rbias_arr_total'] = cfg['Rbias_arr'] +  cfg['Rbias_cable']
    ## Include 50 ohms from RC.
    cfg['Rfb_total'] = cfg['Rfb'] + 50.
    # Yuck, fix me.
    if cfg['use_srdp_Rshunt']:
        cfg['jshuntfile'] = os.getenv('MAS_SCRIPT')+'/srdp_data/'+cfg['array']+ \
            '/johnson_res.dat.C%02i'
    return cfg


#
# IV branch analysis function
#
SCALE = .100  # uV

def analyze_IV_curve(bias, fb,
                     deriv_thresh=5e-6,
                     scale=SCALE,
                     ):
    results = {'ok': False}
    n = bias.shape[0]
    i = 0
    dy = fb[1:] - fb[:-1]
    dbias = -np.mean(bias[1:] - bias[:-1])
    span = max(5, int(scale/dbias))
    supercon, transend = None, None
    # Look at all places where the derivative is positive.
    pos_idx = (dy[:-span]>0).nonzero()[0]
    # Find the first stable such point; that's the transition
    for i in pos_idx:
        if np.median(dy[i:i+span]) > 0:
            trans = i
            break
    else:
        return results
    # Look for large negative derivatives (supercond branch)
    big_idx = (dy[i:-span] < -deriv_thresh).nonzero()[0] + i
    for i in big_idx:
        if np.median(dy[i:i+span]) < -deriv_thresh:
            transend = i
            break
    else:
        # Ok if we didn't find the supercond branch.
        transend = len(bias)-2
        #return results
    trans_bias = bias[trans]
    normal_idx = ((bias > trans_bias+0.2)).nonzero()[0]

    ok = len(normal_idx) > 1
    if not ok:
        return results
    results = dict(zip(['ok', 'trans_begin', 'trans_end', 'trans_bias'],
                       [ok, trans, transend, trans_bias]))
    # Fit normal branch
    normfit = np.polyfit(bias[normal_idx], fb[normal_idx], 1)
    Rnorm, offset = normfit
    results.update(zip(['norm_offset', 'Rnorm', 'norm_idx0', 'norm_idx1'], \
                           [offset, Rnorm, min(normal_idx), max(normal_idx)]))
    # Fit super-conducting branch
    superfit = np.polyfit(bias[transend:], fb[transend:], 1)
    results.update(zip(['super_offset', 'Rsuper', 'super_idx0', 'super_idx1'],
                       [superfit[1], superfit[0], transend, fb.shape[0]]))

    return results

