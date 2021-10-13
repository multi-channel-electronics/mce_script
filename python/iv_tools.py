from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import range
from past.utils import old_div
from builtins import object
import os

import subprocess as sp
import numpy as np

from auto_setup.util import mas_path
from mce_data import MCEFile

from auto_setup import config

class runfile_block(object):
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
        if self.data_cols is not None:
            data_cols = self.data_cols
        for c in range(value.shape[1]):
            self.write_vector(key % data_cols[c], value[:,c], format)

    def close(self):
        if self.fout is not None:
            self.fout.close()
        self.fout


class adict(object):
    """
    Just a holder for arrays.  Members of a particular types, but with
    the same shape are added with the "define" method.

    Set all member arrays, for some index, with a dictionary passed to
    add_item.
    """
    def __init__(self, keys=None, types=None, shape=None):
        self.keys = []
        if keys is not None:
            self.define(keys, types, shape)
    def define(self, keys, types, shape):
        for k, t in zip(keys,types):
            setattr(self, k, np.zeros(shape, dtype=t))
            self.keys.append(k)
    def add_item(self, index, source):
        for k, v in source.items():
            if k in self.keys:
                getattr(self,k)[index] = v

def read_ascii(filename, data_start=0, comment_chars=[]):
    data = []
    for line in open(filename):
        w = line.split()
        if len(w) == 0 or w[0][0] in comment_chars: continue
        data.append([float(x) for x in w])
    return np.transpose(data)


class IVData(object):
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
        if filename is not None:
            self.read(filename, biasfile, runfile)

    def read(self, filename, biasfile=None, runfile=True):
        """
        Load IV feedback data; extract and unwrap it.  Load associated
        runfile and determine the bias values (in DAC units) applied.
        """
        self.mcefile = MCEFile(filename, runfile=runfile)
        self.runfile = self.mcefile.runfile
        self.mcedata = self.mcefile.Read(row_col=True,
                                         unwrap=True,
                                         unfilter='DC').data
        self.data_cols = np.array(self.mcefile._NameChannels(row_col=True)[1])
        # Also load the list of TES bias values... this has got to go.
        if biasfile is None:
            biasfile = filename + '.bias'
        self.bias_dac = read_ascii(biasfile, comment_chars=['<', '#'])[0]
        self.n_row, self.n_col, self.n_pts = self.mcedata.shape
        if self.bias_dac.shape[0] != self.n_pts:
            raise RuntimeError('weird .bias file')
    
    def compute_physical(self, ar_par):
        """
        Convert biases and feedbacks to physical units, using array
        parameters passed in through dictionary ar_par.
        """
        # Differentials
        ## TES bias DAC voltage, per DAC unit
        self.dbias_ddac = old_div(ar_par['bias_DAC_volts'], 2**ar_par['bias_DAC_bits'])
        R33, Rfb = 49.9, ar_par['Rfb_total']
        fb_DAC_volts = ar_par['fb_DAC_amps'] * Rfb * R33 / (R33 + Rfb)
        ## SQ1 FB DAC voltage, per DAC unit
        self.dfb_ddac = old_div(fb_DAC_volts, 2**ar_par['fb_DAC_bits'])
        ## TES current, per unit FB DAC voltage
        self.di_dfb = old_div(1, (ar_par['M_ratio']*Rfb))

        ## Get the bias configuration, which includes per-channel sign
        ## of the feedback -> power conversion.  Another way to do
        ## this would be to put it directly into dfb_ddac.
        line_map = BiasLineMapping.from_array_params(ar_par).for_IV_data(self)

        ## Vectors
        self.bias_v = self.bias_dac * self.dbias_ddac
        self.fb_v = self.mcedata * line_map.sign[:,:,None] * self.dfb_ddac

    def compute_tes(self, iv_data, ar_par, Rshunt, bias_map,
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
        Rb = ar_par['Rbias_arr_total'][bias_map.virt_line]
        self.tes_v = 1e6 * Rshunt.R[:,:,None] * \
            (old_div(self.bias_v[None,None,:],Rb[:,:,None]) - self.tes_i*1e-6)
        ## The resistance vector; just the ratio of voltage to current.
        self.tes_R = old_div(self.tes_v, self.tes_i)
        ## The power
        self.tes_P = self.tes_v * self.tes_i
        ## More branch analysis...
        self.ok_rc = list(zip(*iv_data.ok.nonzero()))
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
        self.tes_fracRn = old_div(self.tes_R, iv_data.R_norm.reshape((nr, nc, 1)))
        ## Responsivity as function of bias, including FB sign correction.
        self.resp = self.di_dfb * self.dfb_ddac * 1e-6*self.tes_v * \
            (1 - old_div(Rshunt.R.reshape((nr, nc, 1)),self.tes_R))
        if ar_par.get('preserve_resp_sign', False):
            self.resp *= bias_map.sign[:,:,None]

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
        if cols is None:
            cols = list(range(self.n_col))
        if rows is None:
            rows = list(range(self.n_row))
        for c in cols:
            for r in rows:
                det = analyze_IV_curve(filedata.bias_v, filedata.fb_v[r,c],
                                       **kwargs)
                self.add_item((r, c), det)
        

class TESShunts(object):
    def __init__(self, shape):
        self.R = np.zeros(shape, 'float')
        self.ok = np.zeros(shape, 'bool')

    @classmethod
    def from_columns_file(cls, shape, filename, data_cols=[0,1,2]):
        """
        Load R from an ascii file.  'shape' should be (n_row, n_col).
        The `data_cols` should be a list of the columns that
        correspond to detector column, row, and R in Ohms.
        """
        self = cls(shape)
        for line in open(filename):
            w = line.split()
            if len(w) == 0 or w[0][0] == '#':
                continue
            col, row, R = [cast(w[i]) for cast,i in zip((int,int,float), data_cols)]
            self.R[row,col] = R
            self.ok[row,col] = True
        return self

    @classmethod
    def from_srdp_files(cls, shape, filename_template, data_cols):
        self = cls(shape)
        for c in data_cols:
            sd = read_ascii(filename_template%c, comment_chars=['#'])
            rows, Rs = sd[0].astype('int'), sd[1]
            self.R[rows, c] = Rs
            self.ok[rows, c] = True
        return self

class BiasLineMapping(object):
    """
    Encapsulate sufficient information to go back and forth between
    (row,col), data, and TES bias line mappings.  In cases where n_row
    is not explicitly specified, n_row = 1 is assumed.
    """
    def __init__(self, n_row, n_col, n_line):
        self.n_row = n_row
        self.n_col = n_col
        self.n_line = n_line
        self.phys_line = np.zeros((n_row, n_col), int)
        self.virt_line = np.zeros((n_row, n_col), int)
        self.mask = np.zeros((n_row, n_col), bool)
        self.sign = np.ones((n_row, n_col), int)
        self.optim = np.zeros((n_row, n_col), bool)

    def for_IV_data(self, filedata):
        # Sub-select columns and (possibly) expand from n_row=1 to filedata.n_row.
        n_row, n_col = filedata.n_row, filedata.n_col
        # New object with structure to match data
        output = self.__class__(n_row, n_col, self.n_line)
        for attr in ['phys_line', 'virt_line', 'mask', 'sign', 'optim']:
            self_data, output_data = getattr(self, attr), getattr(output, attr)
            if self.n_row == 1:
                # Simple expansion
                output_data[:,:] = self_data[0,filedata.data_cols]
            else:
                # Mask / collapse
                output_rows = np.arange(output.n_row)
                row_mask = (output_rows < self.n_row)
                output_data[row_mask,:] = self_data[output_rows[row_mask]]\
                    [:,filedata.data_cols]
        return output

    def phys_line_mask(self, line):
        return (self.phys_line == line) * self.mask

    def virt_line_mask(self, line):
        return (self.virt_line == line) * self.mask

    @classmethod
    def from_array_params(cls, ar_par):
        n_line = ar_par['n_bias_lines']

        if ar_par['bias_line_scheme'] == 'per-column':
            line_map = ar_par['bias_lines']
            n_row, n_col = 1, len(line_map)
            line_data = ar_par['bias_lines'][None,:]
            self = cls(n_row, n_col, n_line)
            self.mask[:,:] = True
            self.phys_line[:,:] = line_data % n_line
            self.virt_line[:,:] = line_data.copy()
            self.sign[:,:] = np.ones((n_row,n_col))
            self.optim[:,:] = True

        elif ar_par['bias_line_scheme'] == 'per-detector':
            scheme_file = os.path.join(
                os.path.split(ar_par['source_file'])[0],
                ar_par['bias_line_filename'])
            row, col, line, renorm, optim = read_ascii(
                scheme_file,comment_chars='#').astype('int')
            n_row, n_col = row.max()+1, col.max()+1
            self = cls(n_row, n_col, n_line)
            self.mask[row,col] = True
            self.phys_line[row,col] = line % n_line
            self.virt_line[row,col] = line
            self.sign[row,col] = renorm
            self.optim[row,col] = optim

        else:
            raise ValueError("unknown bias_line_scheme = '%s'" % \
                ar_par['bias_line_scheme'])

        # Also allow a per-column sign correction to the signal.
        if 'fb_normalize' in ar_par:
            self.sign *= ar_par['fb_normalize'][None,:]

        return self


class logger(object):
    def __init__(self, verbosity=0, indent=True):
        self.v = verbosity
        self.indent = indent
    def write(self, s, level=0):
        if level <= self.v:
            if self.indent:
                print(' '*level, end=' ')
            print(s)
    def __call__(self, *args, **kwargs):
        return self.write(*args, **kwargs)

def load_array_params(filename=None, array_name=None):
    if array_name is None:
        array_name = open(os.path.join(mas_path().data_root(),
            'array_id')).readline().strip()
    if filename is None:
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
    # Check/add "bias_line_map_scheme"
    if not 'bias_line_scheme' in cfg:
        cfg['bias_line_scheme'] = 'per-column'
    return cfg


#
# IV branch analysis function
#
SCALE = .100  # uV

def analyze_IV_curve(bias0, fb0,
                     deriv_thresh=5e-3,
                     scale=SCALE,
                     smoother_mode=0,
                     ):
    results = {'ok': False}

    # Curve feature analysis works better with smoothed curves.
    if smoother_mode == 0:
        sl, fb = slice(0, len(fb0)), fb0
        bias = bias0
    elif smoother_mode == 1:
        _, sl, fb = smooth(fb0, 4)
        bias = bias0[sl]
    else:
        raise ValueError('Unknown smoother_mode: %i' % smoother_mode)

    n = bias.shape[0]
    i = 0
    dbias = -np.mean(bias[1:] - bias[:-1])
    dy = old_div((fb[1:] - fb[:-1]), dbias)
    span = max(5, int(old_div(scale,dbias)))
    transend = None
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

    # Destroy smoothed curves and refer transition indices back to
    # original inputs.
    del fb, bias
    trans += sl.start
    transend += sl.start

    # Do linear fits on the raw data, not the smoothed data.
    fb, bias = fb0, bias0
    trans_bias = bias[trans]

    normal_idx = ((bias > trans_bias+0.2)).nonzero()[0]

    ok = len(normal_idx) > 1
    if not ok:
        return results
    results = dict(list(zip(['ok', 'trans_begin', 'trans_end', 'trans_bias'],
                       [ok, trans, transend, trans_bias])))
    # Fit normal branch
    normfit = np.polyfit(bias[normal_idx], fb[normal_idx], 1)
    Rnorm, offset = normfit
    results.update(list(zip(['norm_offset', 'Rnorm', 'norm_idx0', 'norm_idx1'], \
                           [offset, Rnorm, min(normal_idx), max(normal_idx)])))
    # Fit super-conducting branch
    superfit = np.polyfit(bias[transend:], fb[transend:], 1)
    results.update(list(zip(['super_offset', 'Rsuper', 'super_idx0', 'super_idx1'],
                       [superfit[1], superfit[0], transend, fb.shape[0]])))

    return results


def smooth(fb, target_segs=3, max_kernel=None):
    """Smooth an input signal using a boxcar filter so that it has a
    certain number of monotonic segments.  The width of the boxcar is
    increased dynamically until the target smoothness is reached.

    Arguments:
      fb: The vector to smooth.
      target_segs: The target number of monotonic segments (for an IV
        curve with supercond, tarnsition, and normal branches, this
        would be 3.
      max_kernel: The largest smoothing kernel to consider.  Defaults
        to len(fb)/10.

    Returns (n_segs, slice, smoothed_fb).  The smoothed_fb is
    typically shortened relative to the input.  The corresponding
    samples of fb (or other vectors) can be selected using slice.
    n_segs is the number of segments detected in the returned result;
    this may be larger than target_segs.

    """
    if max_kernel is None:
        max_kernel = len(fb) // 10
    if max_kernel % 2 == 0:
        max_kernel -= 1
    best = None
    for klen in range(0, max_kernel//2):
        fb1 = old_div(np.convolve(fb, np.ones(klen*2+1), 'valid'), (klen*2+1))
        dy = np.diff(fb1)
        sc = (dy[1:]*dy[:-1] < 0).sum()
        if best is None or sc < best[0]:
            best = (sc, slice(klen, len(fb)-klen), fb1)
        if sc <= target_segs:
            break
    return best
