# vim: ts=4 sw=4 et
import time, os, glob
import auto_setup.util as util
from numpy import *
import numpy as np
from mce_data import MCERunfile, MCEFile

import servo

def go(tuning, rc, filename=None):

    ok, servo_data = acquire(tuning, rc, filename=filename)
    if not ok:
        raise RuntimeError, servo_data['error']

    sq = RSServo(servo_data['filename'], tuning=tuning)
    lock_points = sq.reduce()
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])

    # Return dictionary of relevant results
    lock_points['super_servo'] = True
    lock_points['data_shape'] = sq.data_shape
    lock_points['cols'] = sq.cols
    return lock_points



class RSServo(servo.SquidData):
    """
    In mux11d tuning, there is one row select (RS) SQUID per detector.
    These are used to mix in a chosen SQ1 at each mux step.
    Optimization involves choosing an SQ1 bias, and finding
    appropriate values for the feedback.

    The bias is shared, per column, and thus can be fast-switched.  So
    it is optimized on a per-column basis.  The feedback is shared
    across rows.
    """
    stage_name = 'RSServo'
    xlabel = 'RS flux / 1000'
    ylabels = {'data': 'SA FB / 1000',
               'error': 'Error / 1000'}
    bias_assoc = 'rowcol'

    def __init__(self, filename=None, tuning=None):
        if tuning == None and filename != None:
            srcdir = os.path.split(filename)[0]
            tuning = os.path.join(srcdir, 'experiment.cfg')
            if not os.path.exists(tuning):
                tuning = None
        servo.SquidData.__init__(self, tuning=tuning)
        self.super_servo = None
        self.data_attrs.append('error')
        if filename != None:
            self.read_data(filename)


    def read_data(self, filename):
        """
        Loads an rs_servo data set.
        """
        rf = MCERunfile(filename+'.run')
        self.rf = rf
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}

        # Determine columns, biases, feedbacks involved in servo
        self.load_ramp_params('RB sq1 bias')
        if self.bias_style == 'select':
            self.bias_assoc = 'col'
        
        # Prime
        self.data_shape = (-1, 1, len(self.cols), len(self.fb))

        # Attempt load after counting bias/fb steps
        self._read_super_bias(filename)

        if not self.super_servo:
            self.bias_assoc = 'col'

    def split(self):
        sq = servo.SquidData.split(self)
        for s in sq:
            s.super_servo = self.super_servo
            s.tuning = self.tuning
        return sq

    def reduce1(self, slope=None):
        self._check_data()
        self._check_analysis(existence=True)

        # Slope handling
        if slope == None:
            # Dodge possibility that params are different lengths...
            s1 = self.tuning.get_exp_param('sq1_servo_gain')[self.cols]
            s2 = self.tuning.get_exp_param('rowsel_servo_gain')[self.cols]
            slope = -sign(s1*s2)
        if not hasattr(slope, '__getitem__'):
            slope = array([slope]*len(self.cols))

        # Make slope either a scalar, or 1 value per curve.
        if any(slope != slope[0]):
            z = zeros(self.data.shape[:-1]).reshape(-1, len(slope))
            slope = (z + slope).ravel()
        else:
            slope = slope[0:1]

        # Categorize curve into hi, and lo regions.
        self.reg = [servo.get_curve_regions(y, extrema=True)
                    for y in self.data*slope[:,None]]
        # Identify first valley, first subsequent peak.
        pairs, oks = [], []
        for r, y in zip(self.reg, self.data*slope[:,None]):
            lo, hi, ok = None, None, False
            while len(r) > 0:
                if r[1][1] > r[1][0]:
                    lo = r[1]
                    break
                r = r[2:]
            if lo and len(r) >= 3:
                hi = r[2]
            if lo and hi:

                # Throw out ramps (max->min and min->max), flat-liners,
                # and very low amplitude responses. 

                minResponse=500  # WARNING - emperical value!
                ok = not ((lo[0] == 0) and (hi[-1] == len(y))) and (abs(y[hi[0]]-y[lo[0]]) > minResponse)

                # May as well get the apparent local extrema.
                pairs.append((argmin(y[lo[0]:lo[1]]) + lo[0],
                              argmax(y[hi[0]:hi[1]]) + hi[0]))
            else:
                pairs.append((0,0))
            oks.append(ok)
        self.analysis['desel_idx'], self.analysis['sel_idx'] = transpose(pairs)
        self.analysis['ok'] = array(oks)

        """
        Compute peak-to-peak response, store in self.analysis.

        For ramp, identify "best" bias, and determine a single set of
        reasonable row select and row deselect flux levels.
        """
        span = amax(self.data, axis=-1) - amin(self.data, axis=-1)
        self.analysis['y_span'] = span
        if self.bias_style == 'ramp':
            # For clarity?
            dshape = self.data_shape[:-1]
            n_bias, n_row, n_col = dshape
            # Choose a SQ1 bias for each row,col
            span = span.reshape(n_bias, -1)
            ok = self.analysis['ok'].reshape((n_bias,-1))
            n_ok = ok.sum(axis=0)
            self.analysis['select_rowcol_sel'] = np.argmax(span*ok,axis=0)
            # Now from those biases, identify row_sel and row_desel
            # values for each row.  Exclude failed analyses, then take
            # a median.
            sel_pair = np.zeros((2,n_row),'int')
            ok = n_ok.reshape(n_row, n_col) > 0  # ok dets
            n_ok = ok.sum(axis=1)                # n_ok dets in row
            sel = np.zeros((2, n_row))
            sel_in = self.analysis['sel_idx'].reshape(n_bias, n_row, n_col), \
                self.analysis['desel_idx'].reshape(n_bias, n_row, n_col)
            bias_idx = self.analysis['select_rowcol_sel'].reshape(n_row, n_col)
            col_idx = np.arange(n_col)
            for r in n_ok.nonzero()[0]:
                for j in [0,1]:
                    s = sel_in[j][bias_idx[r],r,col_idx]
                    sel[j, r] = np.median(s[ok[r]])
        else:
            # Reduce those the sel/desel_idx to one per row:
            n_row, n_col = self.data_shape[-3:-1]
            sel1, sel0, ok = [self.analysis[k].reshape(n_row,n_col)
                              for k in ['sel_idx', 'desel_idx', 'ok']]
            sel = zeros((2,n_row),'int')
            for r in range(n_row):
                if any(ok[r]):
                    # Take the average (not median or left-most) row select
                    # value.  This helps when magnetic fields shift some of the
                    # column's row select responses

                    sel[:,r] = np.average(sel1[r,ok[r]]), np.average(sel0[r,ok[r]])

        # Store those 
        self.analysis['sel_idx_row'] = sel[0]
        self.analysis['desel_idx_row'] = sel[1]
        return self.analysis

    def reduce(self, slope=None):
        """
        Identify low points, high points, store in self.analysis.
        """
        an = self.reduce1(slope=slope)

        # Add feedback keys
        for k in ['desel', 'sel']:
            an[k+'_x'] = self.fb[an[k+'_idx']]
            if self.bias_style=='ramp':
                an[k+'_x_row'] = self.fb[an[k+'_idx_row']]

        # Copy those for plotting
        an['left_x'], an['right_x'] = an['desel_x'], an['sel_x']
        self.analysis = an
        return an
        
    def plot(self, plot_file=None, format=None, data_attr='data'):
        if plot_file == None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))
        if format == None:
            format = self.tuning.get_exp_param('tuning_plot_format')

        # Is this a multi-bias ramp?  If so, split down
        if self.bias_style == 'ramp':
            ss = self.split()
            plot_files = []
            _format = format
            if format == 'pdf':  # make one big pdf
                _format = 'svg'
            for i,s in enumerate(ss):
                s.reduce()
                p = s.plot(plot_file=plot_file+'_b%02i'%i, format=_format,
                           data_attr=data_attr)
                plot_files += p['plot_files']
            # collate into pdf?
            if format == 'pdf':
                ofile = plot_file + '_all.pdf'
                pp = util.plotter.pdfCollator(plot_files, ofile)
                if pp.collate(remove_sources=True):
                    plot_files = [ofile]
            return {'plot_files': plot_files}

        # Now worry about whether we have analysis and data...
        self._check_data()
        self._check_analysis()

        # Display biases as inset text
        n_row, n_col = self.data_shape[-3:-1]
        idx = np.arange(n_row*n_col) 
        if self.bias_assoc == 'row':
            idx /= n_col
        elif self.bias_assoc == 'col':
            idx %= n_col
        ## make one string per bias...
        insets = ['BIAS = %5i' % b for b in self.bias]
        ## then repeat it as needed
        insets = [insets[i] for i in idx]

        # Default data is self.data
        data = getattr(self, data_attr)

        # Plot plot plot
        return servo.plot(
            self.fb, data, self.data_shape[-3:-1],
            self.analysis, plot_file,
            lock_levels=False,
            intervals=data_attr != 'error',
            insets=insets,
            title=self.data_origin['basename'],
            xlabel=self.xlabel,
            ylabel=self.ylabels[data_attr],
            format=format,
            )

    def plot_error(self, *args, **kwargs):
        if not 'data_attr' in kwargs:
            kwargs['data_attr'] = 'error'
        if not 'plot_file' in kwargs:
            kwargs['plot_file'] = os.path.join(self.tuning.plot_dir, '%s' % \
                                  (self.data_origin['basename'] + '_err'))
        return self.plot(*args, **kwargs)
