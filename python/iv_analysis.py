import os, sys, time
from numpy import *
from mce_data import MCEFile
import subprocess as sp

from auto_setup.util import interactive_errors

class cfgFile:
    def __init__(self, filename):
        self.filename = filename

    def get(self, key, dtype=None, single=False):
        data = sp.Popen(['mas_param','-s',self.filename,'get',key], stdout=sp.PIPE).communicate()[0]
        s = data.split('\n')[0].split()
        if dtype == None or dtype == 'string':
            return s
        elif dtype == 'int':
            y = [ int(ss) for ss in s if ss != '']
        elif dtype == 'float':
            y = [ float(ss) for ss in s if ss != '']
        else:
            raise ValueError, 'can\'t handle dtype=\'%s\' '%dtype
        if single:
            return y[0]
        return array(y)

class runfile_block:
    """
    Write (especially) numpy arrays to a runfile-block file.
    """
    def __init__(self, filename, mode='w'):
        self.fout = open(filename, mode)

    def __del__(self):
        self.close()

    def write_scalar(self, key, value, format='%s'):
        self.fout.write(('<%s> '+format+'\n') % (key, value))

    def write_vector(self, key, value, format='%.6f'):
        _value = ' '.join([format % x for x in value])
        self.write_scalar(key, _value)
    
    def write_array(self, key, value, format='%.6f'):
        for c in range(value.shape[1]):
            self.write_vector(key % c, value[:,c], format)

    def close(self):
        if self.fout != None:
            self.fout.close()
        self.fout


def unwrap(data, period):
    ddata = data[...,1:] - data[...,:-1]
    ups = (ddata >  period/2).nonzero()
    dns = (ddata < -period/2).nonzero()
    for r, c, i in zip(*ups):
        data[r, c, i+1:] -= period
    for r, c, i in zip(*dns):
        data[r, c, i+1:] += period

def loadArrayParams(filename=None, array_name=None):
    if array_name == None:
        array_name = open('/data/cryo/array_id').readline().strip()
    if filename == None:
        filename = os.getenv('MAS_TEMPLATE') + '/array_%s.cfg' % array_name
    cfg = cfgFile(filename)
    params = {'array': array_name,
              'source_file': filename}
    schema = [
        ('float', True,  ['Rfb', 'M_ratio', 'default_Rshunt', 'per_Rn_bias',
                          'fb_DAC_amps', 'bias_DAC_bits',
                          'bias_DAC_volts', 'fb_DAC_bits']),
        ('int',   True,  ['ncut_lim', 'use_srdp_Rshunt', 'n_bias_lines', 'bias_step']),
        ('float', False, ['fb_normalize', 'per_Rn_cut', 'psat_cut', 'good_shunt_range',
                          'Rbias_arr', 'Rbias_cable']),
        ('int',   False, ['bias_lines']),
        ]
    for dtype, single, keys in schema:
        for k in keys:
            params[k] = cfg.get(k, dtype, single)
    return params

def read_ascii(filename, data_start=0, comment_chars=[]):
    data = []
    for line in open(filename):
        w = line.split()
        if len(w) == 0 or w[0][0] in comment_chars: continue
        data.append([float(x) for x in w])
    return array(data).transpose()

#
# Main IV analysis routine
#

def analyze_IV_curve(bias, fb, deriv_thresh=5e-6):
    results = {'ok': False}
    n = bias.shape[0]
    i = 0
    dy = fb[1:] - fb[:-1]
    span = 12
    supercon, transend = None, None
    # Look at all places where the derivative is negative.
    neg_idx = (dy[:-span]<0).nonzero()[0]
    # Find the first stable such point.
    for i in neg_idx:
        if median(dy[i:i+span]) <= 0:
            supercon = i
            break
    else:
        return results
    # Look for large derivatives (transition)
    big_idx = (dy[i:-span] > deriv_thresh).nonzero()[0] + i
    for i in big_idx:
        if median(dy[i:i+span]) > deriv_thresh:
            transend = i
            break
    else:
        return results
    trans_bias = bias[supercon]
    normal_idx = ((bias > trans_bias+0.2)*(bias < trans_bias + 0.8)* \
                      (arange(n) <= n*3/4)).nonzero()[0]
    ok = len(normal_idx) > 1
    if not ok:
        return results
    results = dict(zip(['ok', 'supercon', 'trans_end', 'trans_bias'],
                       [ok, supercon, transend, trans_bias]))
    # Fit normal branch
    normfit = polyfit(bias[normal_idx], fb[normal_idx], 1)
    Rnorm, offset = normfit
    results.update(zip(['norm_offset', 'Rnorm', 'norm_idx0', 'norm_idx1'], \
                           [offset, Rnorm, min(normal_idx), max(normal_idx)]))
    # Fit super-conducting branch
    superfit = polyfit(bias[transend:], fb[transend:], 1)
    results.update(zip(['super_offset', 'Rsuper', 'super_idx0', 'super_idx1'],
                       [superfit[1], superfit[0], transend, fb.shape[0]]))

    return results

# Some basic MCE data
MCE_params = {
    'periods': {1: 2**19, 9: 2**24, 10: 2**28},
    'filtered': {1: 0, 9: 1, 10: 1},
    'filter_gains': {1: 1., 9: 1216., 10: 1216.}
    }

#
# Main
#

t0 = time.time()

from optparse import OptionParser
o = OptionParser(usage="%prog [options] [iv_filename]")
o.add_option('--plot-dir', default=None)
o.add_option('--verbosity', default=2, type='int')
o.add_option('--rf-file', default=None)
o.add_option('--array', default=None)
o.add_option('--array-file', default=None)
o.add_option('--with-rshunt-bug', default=0, type='int')
o.add_option('-i','--interactive', action='store_true')
opts, args = o.parse_args()

if opts.interactive:
    interactive_errors(True)

if len(args) != 1:
    o.error('Give exactly 1 IV filename.')

# Source data
filename = args[0]

# Destination for plots
if opts.plot_dir == None:
    opts.plot_dir = filename + '_data'
if opts.plot_dir == 'none':
    opts.plot_dir = None
else:
    if not os.path.exists(opts.plot_dir):
        os.makedirs(opts.plot_dir)

# Runfile output
if opts.rf_file == None:
    opts.rf_file = filename + '.out'
if opts.rf_file == 'none':
    opts.rf_file = None

# Load data and properties
filedata = MCEFile(filename)

if opts.array == None:
    opts.array = filedata.runfile.Item('FRAMEACQ','ARRAY_ID',array=False).strip()

# Load array description
ar_par = loadArrayParams(filename=opts.array_file, array_name=opts.array)

# Adjust...
ar_par['Rbias_arr'] += ar_par['Rbias_cable']  # Include cable
ar_par['Rfb'] += 50.                          # Include 50 ohms from RC

if ar_par['use_srdp_Rshunt']:
    ar_par['jshuntfile'] = os.getenv('MAS_SCRIPT')+'/srdp_data/'+ar_par['array']+ \
                           '/johnson_res.dat.C%02i'

            
# DAC to Voltage conversions.
## FB is a current DAC, so effective output voltage depends on
## bridge resistance (R33 ~ 50 ohms) and R_fb.
r = 49.9  #R33
Rfb = ar_par['Rfb']
fb_DAC_volts = ar_par['fb_DAC_amps'] * Rfb * r / (r + Rfb)
dfb_ddac = fb_DAC_volts / 2**ar_par['fb_DAC_bits']

## bias is voltage DAC
dbias_ddac = ar_par['bias_DAC_volts'] / 2**ar_par['bias_DAC_bits']

data_mode = filedata.runfile.Item('HEADER','RB rc1 data_mode',
                                  type='int',array=False)
filtgain = MCE_params['filter_gains'][data_mode]
period = MCE_params['periods'][data_mode]

# Load, unwrap, rescale data to SQ1 FB DAC units.
data = filedata.Read(row_col=True).data
data_cols = array(filedata._NameChannels(row_col=True)[1])

unwrap(data, period)
unwrap(data, period/2)
data *= ar_par['fb_normalize'][data_cols].reshape(1,-1,1) / filtgain

# The size of the problem
n_row, n_col, n_pts = data.shape

# Read bias values
raw_bias = read_ascii(filename+'.bias', comment_chars=['<', '#'])[0]
if raw_bias.shape[0] != n_pts:
    raise RuntimeError, 'weird .bias file'

# Read shunt data
Rshunt = zeros((n_row, n_col))
if ar_par['use_srdp_Rshunt']:
    for c in range(n_col):
        sd = read_ascii(ar_par['jshuntfile']%c, comment_chars=['#'])
        rows, Rs = sd[0].astype('int'), sd[1]
        Rshunt[rows, c] = Rs

shunts_ok = (ar_par['good_shunt_range'][0] < Rshunt) * \
    (Rshunt < ar_par['good_shunt_range'][1])

Rshunt[~shunts_ok] = ar_par['default_Rshunt']
# AR3 exception (puke)
if ar_par['array'] == 'AR3':
    Rshunt[(col >= 24)*~shunts_ok] = 0.0007

# To volts
bias = raw_bias * dbias_ddac
fb = data * dfb_ddac

supercon_index = zeros((n_row, n_col), dtype='int')
transend_index = zeros((n_row, n_col), dtype='int')
iv_ok = zeros((n_row, n_col), dtype='bool')
bias_offsets = zeros((n_row, n_col), dtype='float')
Rnorm = zeros((n_row, n_col), dtype='float')
span = 12


iv_results = {}

# Translation table for per-det results
keys = ['ok',
        'norm_offset', 'norm_idx0', 'norm_idx1', 'R_norm',
        'super_offset', 'super_idx0', 'super_idx1', 'R_super',
        'psat',
]
dtypes = ['bool',
          'float', 'int', 'int', 'float',
          'float', 'int', 'int', 'float',
          'float',
]

class adict:
    def __init__(self, keys=None, types=None, shape=None):
        self.keys = []
        if keys != None:
            self.define(keys, types, shape)
    def define(self, keys, types, shape):
        for k, t in zip(keys,types):
            setattr(self, k, zeros(shape, dtype=t))
            self.keys.append(k)
    def add_item(self, index, source):
        for k, v in source.iteritems():
            if k in self.keys:
                getattr(self,k)[index] = v

iv_data = adict(keys, dtypes, (n_row, n_col))
for c in range(n_col):
    for r in range(n_row):
        det = analyze_IV_curve(bias, fb[r,c])
        iv_data.add_item((r, c), det)
ok_rc = zip(*iv_data.ok.nonzero())

# Remove offset from feedback data and convert to TES current (uA)
di_dfb = 1 / (-ar_par['M_ratio']*Rfb)
i_tes = 1e6 * di_dfb * (fb - iv_data.norm_offset.reshape(n_row, n_col, 1))

# Compute v_tes (uV) from bias voltage and i_tes
Rbias = ar_par['Rbias_arr'][ar_par['bias_lines'][data_cols]]  # per-column
v_tes = 1e6 * Rshunt.reshape(n_row, n_col,1)* \
    (bias.reshape(1,1,-1)/Rbias.reshape(1,-1,1) - i_tes*1e-6)

# Recompute R_normal, saturation power
R = v_tes / i_tes
for r, c in ok_rc:
    i0, i1 = iv_data.norm_idx0[r,c], iv_data.norm_idx1[r,c]+1
    iv_data.R_norm[r,c] = R[r,c,i0:i1].mean()

perRn = R / iv_data.R_norm.reshape(n_row,n_col,1)
for r, c in ok_rc:
    norm_region = (perRn[r,c,:iv_data.super_idx0[r,c]] > 0.5).nonzero()[0]
    if norm_region.shape[-1] == 0:
        continue
    i0 = norm_region.max()
    iv_data.psat[r,c] = v_tes[r,c,i0] * i_tes[r,c,i0]

# Evaluate set points at target bias
def get_setpoints(perRn, idx, target):
    setpoints = zeros(perRn.shape[:2], dtype='int')
    for r, c in ok_rc:
        upper_region = (perRn[r,c,:idx[r,c]] > target).nonzero()[0]
        if upper_region.shape[-1] == 0:
            continue
        setpoints[r,c] = upper_region.max()
    return setpoints

# Bias choice; lo, choice, hi
setpoints = array([
        get_setpoints(perRn, iv_data.super_idx0, ar_par['per_Rn_bias']),
        get_setpoints(perRn, iv_data.super_idx0, 0.2),
        get_setpoints(perRn, iv_data.super_idx0, 0.8),
        ])

# Convert to DAC values
setpoints_dac = raw_bias[setpoints]

# Choose a bias for each bias line.
n_lines = ar_par['n_bias_lines']
bias_lines = ar_par['bias_lines'][data_cols] % n_lines
bias_points_dac = zeros(n_lines, dtype='float')
for line in range(n_lines):
    select = (bias_lines==line).reshape(1, n_col) * iv_data.ok
    dac = setpoints_dac[0,select]
    select = (dac>0)*(dac < 20000)
    bias_points_dac[line] = median(dac[select])

# Round.
bstep = ar_par['bias_step']
bias_points_dac = (bias_points_dac/bstep).round().astype('int')*bstep

# Evaluate perRn of each det at the chosen bias point
bias_points_dac_ar = bias_points_dac[bias_lines].reshape(1,n_col)
set_data = adict(
    ['index', 'perRn', 'v_tes', 'i_tes', 'p_tes', 'resp', 'keep_rec'],
    [int, float, float, float, float, float, bool],
    (n_row, n_col))

for r,c in ok_rc:
    i = (raw_bias <= bias_points_dac[bias_lines[c]]).nonzero()[0]
    if len(i) == 0: continue
    set_data.index[r,c] = i[0]
    set_data.perRn[r,c] = perRn[r,c,i[0]]
    set_data.v_tes[r,c] = v_tes[r,c,i[0]]
    set_data.i_tes[r,c] = i_tes[r,c,i[0]]

set_data.p_tes = set_data.v_tes*set_data.i_tes

# Responsivity
if opts.with_rshunt_bug:
    # Simulate bug in IDL version
    Rshunt_eff = Rshunt[:,n_col-1:]
else:
    Rshunt_eff = Rshunt

set_data.resp = -di_dfb*dfb_ddac * 1e-6*set_data.v_tes * \
    (1 - Rshunt_eff/set_data.perRn/iv_data.R_norm)
set_data.resp[~iv_data.ok] = 0.

# Cutting, cutting.

ok = iv_data.ok
p, r = set_data.p_tes[ok], set_data.perRn[ok]
p0,p1 = ar_par['psat_cut']
r0,r1 = ar_par['per_Rn_cut']

set_data.keep_rec[ok] = (p0<p)*(p<p1)*(r0<r)*(r<r1)

#
# Report
#

if opts.verbosity >= 2:
    print 'Good normal branches found in each column:'
    for c in range(n_col):
        print 'Column %2i = %4i' % (c, iv_data.ok[:,c].sum())

if opts.verbosity >= 1:
    if opts.with_rshunt_bug:
        print 'Rshunt bug is in!.'
        print
    print 'Recommended biases for target of %10.4f Rn' % ar_par['per_Rn_bias']
    for l in range(n_lines):
        print 'Line %2i = %6i' % (l, bias_points_dac[l])
    print
    print 'Cut limits at recommended biases:'
    print '%% R_n   %10.6f %10.6f' % (r0,r1)
    print 'Po (pW) %10.6f %10.6f' % (p0, p1)
    print
    print 'Total good normal branches              =  %4i' % iv_data.ok.sum()
    print 'Number of detectors within cut limits   =  %4i' % sum(set_data.keep_rec)

#
# Runfile block !
#


if opts.rf_file != None:
    if opts.verbosity >= 1:
        print 'Writing runfile block to %s' % opts.rf_file
    rf_out = runfile_block(opts.rf_file)
    rf_out.write_scalar('IV','')
    rf_out.write_scalar('iv_file', filename)
    rf_out.write_scalar('target_percent_Rn', 100*ar_par['per_Rn_bias'], '%i')
    rf_out.write_vector('bias_resistances_used', ar_par['Rbias_arr'], '%.3f')
    rf_out.write_vector('rec_biases', bias_points_dac, '%i')
    rf_out.write_vector('cut_per_Rn', ar_par['per_Rn_cut'], '%.6f')
    rf_out.write_vector('cut_bias_power(pW)', ar_par['psat_cut'], '%6f')
    rf_out.write_scalar('iv_curves_found', iv_data.ok.sum(), '%i')
    rf_out.write_scalar('detectors_within_cut', set_data.keep_rec.sum(), '%i')
    rf_out.write_array('Responsivity(W/DACfb)_C%i', set_data.resp, '%0.5e')
    rf_out.write_array('Percentage_Rn_C%i', set_data.perRn, '%.6f')
    rf_out.write_array('Bias_Power(pW)_C%i', set_data.p_tes, '%.5f')
    rf_out.write_array('Bias_Voltage(uV)_C%i', set_data.v_tes, '%.6f')
    rf_out.write_array('cut_rec_C%i', (~set_data.keep_rec).astype('int'), '%i')
    rf_out.write_scalar('/IV','')
    rf_out.close()
    
#
# Plot :P
#

if opts.plot_dir != None:
    if opts.verbosity >= 1:
        print 'Plotting (%8.3f)' % (time.time() - t0)

    from auto_setup.util.plotter import *
    import biggles as bg

    # Three columns need 3 labels
    x_labels = [ 'TES V (uV)', 'TES P (pW)', 'Det bias (A)' ]

    for c in range(n_col):
        print 'Plotting column %2i' % c
        file_pattern = os.path.join(opts.plot_dir, 'IV_plots_C%02i_%%02i.png' % c)
        pi = stackedPager(
            page_shape=(6,3),
            shape=(n_row,3),
            filename=file_pattern,
            img_size=(700, 700),
        )
        for r, pc, p in pi:
            xl, yl = None, None
            if pc == 0:
                # TES I vs TES V (transition and normal)
                idx = arange(0, iv_data.super_idx0[r,c])
                if len(idx) == 0: continue
                x, y = v_tes[r,c,idx], i_tes[r,c,idx]
            elif pc == 1:
                # R_eff vs P (transition and normal)
                idx = arange(0, iv_data.super_idx0[r,c])
                if len(idx) == 0: continue
                x, y = v_tes[r,c,idx]*i_tes[r,c,idx], v_tes[r,c,idx]/i_tes[r,c,idx]
                xl, yl = (0, x.max()), (0, y.max())
            elif pc == 2:
                # Shunt I vs shunt V (super-cond)
                idx = arange(iv_data.super_idx0[r,c], n_pts)
                if len(idx) == 0: continue
                i_super = 1e6 * di_dfb * (fb[r,c,idx] - iv_data.super_offset[r,c])
                v_super = 1e6 * bias[idx]/Rbias[c]
                x, y = v_super, i_super
                xl, yl = (0, 1e2), (0, 1e2)
            if x != None and x.shape[0] > 0:
                p.add(bg.Curve(x, y))
                if xl != None: p.xrange = xl
                if yl != None: p.yrange = yl

if opts.verbosity >= 1:
    print 'Analysis complete (%8.3f)' % (time.time() - t0)
