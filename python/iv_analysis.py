#!/usr/bin/python

import os, sys, time
import numpy as np
from numpy import *
from mce_data import MCEFile, unwrap
from auto_setup.util import mas_path

from auto_setup.util import interactive_errors

import iv_tools


#
# Main
#

t0 = time.time()

from optparse import OptionParser
o = OptionParser(usage="%prog [options] [iv_filename]")
o.add_option('--plot-dir', default=None)
o.add_option('--summary-only', action='store_true')
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

# Messaging
printv = iv_tools.logger(opts.verbosity)
seterr(divide='ignore') # numpy - suppress /0 warnings.

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
printv('Loading data...', 1)
filedata = iv_tools.IVData(filename)

if opts.array == None:
    opts.array = filedata.runfile.Item('FRAMEACQ','ARRAY_ID',array=False).strip()

# Load array description
ar_par = iv_tools.load_array_params(filename=opts.array_file, array_name=opts.array)

# Get bias and feedback, in physical units, based on array parameters.
filedata.compute_physical(ar_par)

# The size of the problem
n_row, n_col, n_pts = filedata.mcedata.shape

# Set up array with bias line associated with each detector.
bias_map = iv_tools.BiasLineMapping.from_array_params(ar_par).for_IV_data(filedata)

# Read shunt data?
if ar_par['use_Rshunt_file'] != 0:
    # Split format string into tokens
    fmt = ar_par['Rshunt_format'].split()
    if fmt[0] == 'detector_list':
        # Args are column indices (col, row, Rshunt)
        cols = map(int, fmt[1:])
        Rshunt = iv_tools.TESShunts.from_columns_file(
            (n_row,n_col), ar_par['Rshunt_filename'], data_cols=cols)
        Rshunt.R[~Rshunt.ok] = ar_par['default_Rshunt']
        printv('Read %i shunt resistances from %s' % \
                   (Rshunt.ok.sum(), ar_par['Rshunt_filename']), 2)
    else:
        raise ValueError, "unknown shunt_format = '%s'" % fmt[0]
else:
    Rshunt = iv_tools.TESShunts((n_row, n_col))
    Rshunt.R[:,:] = ar_par['default_Rshunt']
    Rshunt.ok[:,:] = True

printv('Analyzing...', 1)
iv_data = iv_tools.IVBranches((n_row, n_col))
supercond_thresh = ar_par.get('supercond_thresh', 5e-3)  # This is not a good default.
iv_data.analyze_curves(filedata, deriv_thresh=supercond_thresh)
ok_rc = zip(*iv_data.ok.nonzero())

# Using the branch analysis in iv_data, and the resistances in Rshunt
# and ar_par, compute loading properties of each TES.
filedata.compute_tes(iv_data, ar_par, Rshunt, bias_map)

# Evaluate set points at target bias and lo, hi points
setpoints = array([
        filedata.get_setpoints(iv_data, ar_par['per_Rn_bias']),
        filedata.get_setpoints(iv_data, 0.2),
        filedata.get_setpoints(iv_data, 0.8),
        ])

# Convert to DAC values
setpoints_dac = filedata.bias_dac[setpoints]

# Choose a bias for each bias line.
bias_points_dac = zeros(bias_map.n_line, dtype='float')
for line in range(bias_map.n_line):
    # Consider detectors from this line...
    select = bias_map.phys_line_mask(line)
    # ... that have valid IV analysis and have been flagged for use in optimization.
    select *= iv_data.ok * bias_map.optim
    dac = setpoints_dac[0,select]
    select = (dac>0)*(dac < 20000)
    bias_points_dac[line] = median(dac[select])

# Round.
bstep = ar_par['bias_step']
bias_points_dac = (bias_points_dac/bstep).round().astype('int')*bstep

# Evaluate perRn of each det at the chosen bias point
bias_points_dac_ar = bias_points_dac[bias_map.phys_line]
set_data = iv_tools.adict(
    ['index', 'R', 'perRn', 'v_tes', 'i_tes', 'p_tes', 'resp', 'keep_rec'],
    [int, float, float, float, float, float, float, bool],
    (n_row, n_col))

for r,c in ok_rc:
    i = (filedata.bias_dac <= bias_points_dac[bias_map.phys_line[r,c]]).nonzero()[0]
    if len(i) == 0: continue
    set_data.index[r,c] = i[0]
    set_data.R[r,c] = filedata.tes_R[r,c,i[0]]
    set_data.perRn[r,c] = filedata.tes_fracRn[r,c,i[0]]
    set_data.v_tes[r,c] = filedata.tes_v[r,c,i[0]]
    set_data.i_tes[r,c] = filedata.tes_i[r,c,i[0]]
    set_data.resp[r,c] = filedata.resp[r,c,i[0]]
    set_data.p_tes[r,c] = filedata.tes_P[r,c,i[0]]

# Kill the bad ones though
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

printv('Good normal branches found in each column:', 2)
for c in range(n_col):
    printv('Column %2i = %4i' % (filedata.data_cols[c], iv_data.ok[:,c].sum()), 2)

if printv.v >= 1:
    if opts.with_rshunt_bug:
        print 'Rshunt bug is in!.'
    print 'Recommended biases for target of %10.4f Rn' % ar_par['per_Rn_bias']
    for l in range(bias_map.n_line):
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
    printv('Writing runfile block to %s' % opts.rf_file, 1)
    rf_out = iv_tools.runfile_block(opts.rf_file, data_cols=filedata.data_cols)
    rf_out.write_scalar('IV','')
    rf_out.write_scalar('iv_file', filename)
    rf_out.write_scalar('target_percent_Rn', 100*ar_par['per_Rn_bias'], '%i')
    rf_out.write_vector('bias_resistances_used', ar_par['Rbias_arr_total'], '%.3f')
    rf_out.write_vector('rec_biases', bias_points_dac, '%i')
    rf_out.write_vector('cut_per_Rn', ar_par['per_Rn_cut'], '%.6f')
    rf_out.write_vector('cut_bias_power(pW)', ar_par['psat_cut'], '%6f')
    rf_out.write_scalar('iv_curves_found', iv_data.ok.sum(), '%i')
    rf_out.write_scalar('detectors_within_cut', set_data.keep_rec.sum(), '%i')
    rf_out.write_array('Responsivity(W/DACfb)_C%i', set_data.resp, '%0.5e')
    rf_out.write_array('Rn_C%i', iv_data.R_norm, '%.5e')
    rf_out.write_array('Percentage_Rn_C%i', set_data.perRn, '%.6f')
    rf_out.write_array('Bias_Power(pW)_C%i', set_data.p_tes, '%.5f')
    rf_out.write_array('Bias_Voltage(uV)_C%i', set_data.v_tes, '%.6f')
    rf_out.write_array('cut_rec_C%i', (~set_data.keep_rec).astype('int'), '%i')
    rf_out.write_scalar('/IV','')
    rf_out.close()
    
printv('Analysis complete (%8.3f)' % (time.time() - t0), 1)

#
# Plot :P
#

if opts.plot_dir != None and not opts.summary_only:
    printv('Plotting all data (%8.3f)' % (time.time() - t0), 1)

    from auto_setup.util.plotter import stackedPager
    import biggles as bg

    # Three columns need 3 labels
    x_labels = [ 'TES V (uV)', 'TES P (pW)', 'Det bias (A)' ]

    rows_pp = 6
    for c in range(n_col):
        printv('Plotting column %2i' % filedata.data_cols[c], 1)
        file_pattern = os.path.join(opts.plot_dir, 'IV_plots_C%02i_%%02i.png' % filedata.data_cols[c])
        pi = stackedPager(
            page_shape=(rows_pp,3),
            shape=(n_row,3),
            filename=file_pattern,
            img_size=(700, 700),
        )
        for r, pc, p in pi:
            valid = ok[r,c] and (iv_data.R_norm[r,c] > 0)
            xl, yl = None, None
            if r % rows_pp == 0:
                fr = pi.canvas['plot'][0,pc]
                if pc == 1:
                    fr.title = 'Column %02i Rows %02i-%02i' % \
                        (filedata.data_cols[c], r, r+rows_pp-1)
                else:
                    fr.title = ''
            else:
                fr == None
            if pc == 0:
                # TES I vs TES V (transition and normal)
                #if not valid:
                #    continue
                if fr != None:
                    fr.xlabel = 'V_TES (uV)'
                    fr.ylabel = 'P_TES (pW)'
                idx = arange(0, iv_data.super_idx0[r,c])
                if len(idx) == 0: continue
                x, y = filedata.tes_v[r,c,idx], filedata.tes_P[r,c,idx]
                xl, yl = (0, x.max()), (0, y.max())
            elif pc == 1:
                if fr != None:
                    fr.xlabel = 'TES POWER (pW)'
                    fr.ylabel = 'R_EFF (Ohms)'
                # R_eff vs P (transition and normal)
                if not valid:
                    continue
                idx = arange(0, iv_data.super_idx0[r,c])
                if len(idx) == 0: continue
                x, y = filedata.tes_P[r,c,idx], filedata.tes_R[r,c,idx]
                xl, yl = (0, x.max()), (0, y.max()*1.1)
                # Show bias point on the R plot.
                if iv_data.ok[r,c]:
                    y_at_bias = set_data.R[r,c]
                    p.add(bg.Curve(xl, [y_at_bias, y_at_bias], type='dashed'))
            elif pc == 2:
                if fr != None:
                    fr.xlabel = 'TES BIAS (DAC/1000)'
                    fr.ylabel = 'FB (DAC/1000)'
                # Show data with analysis regions
                y = filedata.mcedata[r,c] / 1000
                x = filedata.bias_dac / 1000
                # Shaded regions; normal, transition, supercond.
                regions = [(iv_data.norm_idx0[r,c],iv_data.norm_idx1[r,c]),
                           (iv_data.trans_idx[r,c],iv_data.super_idx0[r,c]),
                           (iv_data.super_idx0[r,c],iv_data.super_idx1[r,c]-1)]
                colors = ('light blue', 'green', 'pink')
                for reg,col in zip(regions, colors):
                    _x = [x[reg[0]], x[reg[1]]]
                    p.add(bg.FillAbove(_x, [y.min(), y.min()], color=col))
                # IV curve
                ## Make the normal branch cross the center line.
                yl = y.min(), y.max()
                if valid:
                    y_norm = y[iv_data.norm_idx0[r,c]], y[iv_data.norm_idx1[r,c]]
                    y_norm = min(*y_norm), max(*y_norm)
                    yl = max(yl[0], 2*y_norm[0]-y_norm[1]), \
                        min(yl[1], 2*y_norm[1]-y_norm[0])
                # Selected bias value
                xb = bias_points_dac[bias_map.phys_line[r,c]] / 1000.
                p.add(bg.Curve([xb,xb],yl,type='dashed'))
            elif pc == 9:
                # Shunt I vs shunt V (super-cond)
                idx = arange(iv_data.super_idx0[r,c], n_pts)
                if len(idx) == 0: continue
                i_super = 1e6 * filedata.di_dfb * (fb[r,c,idx] - iv_data.super_offset[r,c])
                v_super = 1e6 * bias[idx]/Rbias[c]
                x, y = v_super, i_super
                xl, yl = (0, 1e2), (0, 1e2)
            if x != None and x.shape[0] > 0:
                p.add(bg.Curve(x, y))
                if xl != None: p.xrange = xl
                if yl != None: p.yrange = yl

if opts.plot_dir != None:
    printv('Generating summary plots', 1)

    import matplotlib
    matplotlib.use('agg')
    import pylab as pl

    def get_R_crossing(i):
        """
        Scan the R/Rnormal data to return R/Rnormal at index ramp index i
        for each detector.

        Checks that i is actually insider the transition, returning
        1. (normal) or 0. (superconducting) for out-of-range points.
        """
        # Look up fraction Rn
        RR = filedata.tes_fracRn[:,:,i].copy()
        # Flag normal
        RR[i<=iv_data.trans_idx] = 1.
        # Flag superconducting
        RR[i>iv_data.super_idx0] = 0.
        return RR


    # Loop over bias lines.
    for tes_idx in range(bias_map.n_line):

        # First summary plot:
        #  Count of dets on transition vs. bias
        s_all = ok * bias_map.phys_line_mask(tes_idx)
        s_other = s_all * ~bias_map.optim
        s_opt = s_all * bias_map.optim
        r0,r1 = ar_par['per_Rn_cut']
        n = []
        bi = arange(0, len(filedata.bias_dac), 10)
        for b in bi:
            RR = get_R_crossing(b)
            n.append(((s_opt * (r0 <= RR) * (RR < r1)).sum(),
                      (s_other * (r0 <= RR) * (RR < r1)).sum()))

        n = np.transpose(n)
        pl.figure()
        pl.plot(filedata.bias_dac[bi], n[0])
        pl.plot(filedata.bias_dac[bi], n[1])
        # Show the chosen bias too
        pl.axvline(bias_points_dac[tes_idx], color='k', ls='dashed')
        pl.xlabel('TES BIAS (DAC)')
        pl.ylabel('N_DETS ON TRANSITION')
        pl.title('%s - bias line %i' % (filename, tes_idx))
        pl.savefig(os.path.join(opts.plot_dir, 'IV_det_count_%02i.png' % tes_idx))

        # Second summary plot:
        n = n[0]
        #  For interesting biases, show %Rn distribution.
        if n.max() == 0:
            continue

        targets = ar_par.get('perRn_plot_target_bins')
        if targets == None:
            # Base targets on the dets-on-transition results.
            lo, hi = (n > n.max() / 10).nonzero()[0][[-1,0]]
            lo, hi = filedata.bias_dac[bi[lo]], filedata.bias_dac[bi[hi]]
            targets = (lo, hi, (hi-lo) / 4.99)

        # To a range
        targets = arange(*targets)

        # Convert targets to ramp index
        targetb = [(filedata.bias_dac <= t).nonzero()[0][0] for t in targets]
        ntarg = len(targets)

        # Get percent Rn
        RR = [get_R_crossing(t) for t in targetb]

        pl.clf()
        rbins = arange(0., 1.01, .05)
        for i,t in enumerate(targets):
            pl.subplot(ntarg, 1, 1+i)

            if s_all.sum() > 0:
                pl.hist(RR[i][s_all], bins=rbins, color='green')
            if s_opt.sum() > 0:
                pl.hist(RR[i][s_opt], bins=rbins, color='blue')

            y0 = pl.ylim()[1]
            pl.text(0.5, y0*.9, 'BIAS = %5i' % t,
                    va='top', ha='center', fontsize=11)
            if i==0:
                pl.title('%s - bias line %i (best bias = %i)' % \
                             (filename, tes_idx, bias_points_dac[tes_idx]))

        pl.gcf().set_size_inches(5., 10.)
        pl.savefig(os.path.join(opts.plot_dir, 'IV_det_hist_%02i.png' % (tes_idx)))
        pl.clf()

    printv('Plotting complete (%8.3f)' % (time.time() - t0), 1)

printv('Exiting (%8.3f)' % (time.time() - t0), 1)
