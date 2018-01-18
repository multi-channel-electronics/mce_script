# vim: ts=4 sw=4 et
import time, os, glob
import biggles
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
        if tuning is None and filename is not None:
            srcdir = os.path.split(filename)[0]
            tuning = os.path.join(srcdir, 'experiment.cfg')
            if not os.path.exists(tuning):
                tuning = None
        servo.SquidData.__init__(self, tuning=tuning)
        self.super_servo = None
        self.data_attrs.append('error')
        if filename is not None:
            self.read_data(filename)

        # Setup required for hybrid mux
        self.ishybrid=None
        self.hybrid_rs_multipliers=None
        if self.tuning is not None:
            self.ishybrid = self.tuning.get_exp_param('mux11d_hybrid_row_select',missing_ok=True) 

            if self.ishybrid==1:            
                # If specified, build list of rs multipliers indexed by readout RS to apply later ...
                mux11d_row_select_multipliers = self.tuning.get_exp_param('mux11d_row_select_multipliers',
                                                                          missing_ok=True)
                if mux11d_row_select_multipliers is not None:
                    self.hybrid_rs_multipliers=[]
                    card_nrs_dict={ 'ac' : 41, 'bc1' : 32, 'bc2' : 32, 'bc3' : 32 }
                    # These better be present if hybrid muxing
                    mux11d_row_select_cards=self.tuning.get_exp_param('mux11d_row_select_cards',missing_ok=False)
                    mux11d_row_select_cards_row0=self.tuning.get_exp_param('mux11d_row_select_cards_row0',missing_ok=False)
                    mux11d_mux_order=self.tuning.get_exp_param('mux11d_mux_order',missing_ok=False)
                    for rs in mux11d_mux_order:
                        for (c,cr) in \
                        [(card,range(r0,r0+card_nrs_dict[card])) for \
                         (r0,card) in \
                         zip(mux11d_row_select_cards_row0,mux11d_row_select_cards)]:
                            if rs in cr:
                                hybrid_rs_multiplier=float(mux11d_row_select_multipliers[where(mux11d_row_select_cards==c)])
                                self.hybrid_rs_multipliers.append(hybrid_rs_multiplier)
                    # Done building hybrid_rs_multipliers list
            # Done collecting hybrid mux config
        
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
        if slope is None:
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

        # Optionally, lets select be on upper/lower boundary of RS flux sweep.  Exercise with caution.
        ok_if_rs_on_upper_bndry=self.tuning.get_exp_param('row_select_can_be_on_upper_boundary',missing_ok=True)
        
        # Identify first valley, first subsequent peak.
        pairs, oks = [], []
        for idx, (r, y) in enumerate(zip(self.reg, self.data*slope[:,None])):
            lo, hi, ok = None, None, False
            while len(r) > 0:
                if r[1][1] > r[1][0]:
                    lo = r[1]
                    break
                r = r[2:]
            if lo and len(r) >= 3:
                hi = r[2]
            if lo and hi:
                
                minResponse = self.tuning.get_exp_param('row_select_minimum_response',missing_ok=True) 
                if minResponse is None:
                    # Previous hard-coded empirical value for
                    # backwards compatible
                    minResponse=500 
                    
                # Throws out very low amplitude responses and flat-liners
                ok = (abs(y[hi[0]]-y[lo[0]]) > minResponse)
 
                # What bias,row,col is this?  Use to decide from
                # expt.cfg whether or not select/deselect is allowed
                # to be on the boundaries.
                if ok_if_rs_on_upper_bndry is not None:
                    if self.bias_style == 'select':
                        (row,col)=np.unravel_index(idx,self.data_shape[-3:-1],order='C')
                    elif self.bias_style == 'ramp':
                        (bias,row,col)=np.unravel_index(idx,self.data_shape[:-1],order='C')                    
                    else:
                        raise RuntimeError, 'Unable to unravel by row.'

                if ok_if_rs_on_upper_bndry is None or ok_if_rs_on_upper_bndry[row]==0:
                    # Throw out ramps (max->min and min->max)
                    ok = not ((lo[0] == 0) and (hi[-1] == len(y))) and ok

                # May as well get the apparent local extrema.
                pairs.append((argmin(y[lo[0]:lo[1]]) + lo[0],
                              argmax(y[hi[0]:hi[1]]) + hi[0]))
            else:
                pairs.append((0,0))

            # Throw out ramps (max->min and min->max), flat-liners,
            # and very low amplitude responses.
            oks.append(ok)
        self.analysis['desel_idx'], self.analysis['sel_idx'] = transpose(pairs)
        self.analysis['ok'] = array(oks)

        """
        Compute peak-to-peak response, store in self.analysis.

        For ramp, identify "best" bias, and determine a single set of
        reasonable row select and row deselect flux levels.
        """
        mx, mn = self.data.max(axis=-1), self.data.min(axis=-1)
        self.analysis['y_max'] = mx
        self.analysis['y_min'] = mn
        span = self.analysis['y_span'] = mx - mn
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

        # Apply hybrid rs multipliers if hybrid mux and they're specified
        if self.ishybrid==1 and self.hybrid_rs_multipliers is not None:
            dshape = self.data_shape[:-1]
            n_bias, n_row, n_col = dshape

            for k in ['desel', 'sel']:
                an_by_row_col=an[k+'_x'].reshape(n_bias,n_row,n_col)
                
                for r in range(n_row):
                    if self.hybrid_rs_multipliers[r]!=1.0: # apply multiplier for plotting
                        for ibias in range(n_bias):
                            an_by_row_col[ibias][r]=(an_by_row_col[ibias][r]*self.hybrid_rs_multipliers[r])

        # Copy those for plotting
        an['left_x'], an['right_x'] = an['desel_x'], an['sel_x']
        self.analysis = an
        return an
        
    def plot(self, plot_file=None, format=None, data_attr='data'):
        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' % \
                                         (self.data_origin['basename']))
        if format is None:
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
        # array of fb values to pass to plotting
        fb_arr = self.fb
        
        # Hybrid muxing?  If user specified per-RS multipliers, give
        # plotting an array of fbs
        if self.ishybrid==1 and self.hybrid_rs_multipliers is not None:
            n_bias=self.data_shape[0]
            fb_arr = np.reshape([self.fb]*data.shape[0],data.shape)
            fb_arr_addressed_by_row_col=fb_arr.reshape(self.data_shape)
            
            for ibias in range(n_bias):
                for r in range(n_row):
                    # Apply multiplier for plotting
                    if self.hybrid_rs_multipliers[r]!=1.0: 
                        fb_arr_addressed_by_row_col[ibias][r]=(fb_arr_addressed_by_row_col[ibias][r]*self.hybrid_rs_multipliers[r])
            
        # Plot plot plot
        return servo.plot(
            fb_arr, data, self.data_shape[-3:-1],
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

    def ramp_summary(self):
        """
        If this is an analyzed bias ramp, returns a RampSummary loaded
        with the amplitudes, max and min values, and bias set points.
        """
        rs = RSServoSummary.from_biases(self)
        rs.add_data('y_span', self.analysis['y_span'],
                    ylabel='Amplitude (/1000)')
        rs.add_data('y_max', self.analysis['y_max'],
                    ylabel='Max error (/1000)')
        rs.add_data('y_min', self.analysis['y_min'],
                    ylabel='Min error (/1000)')
        rs.add_data('ok', self.analysis['ok'],
                    ylabel='Curve quality')
        # Turn bias indices into biases; store as analysis.
        idx = self.analysis['select_%s_sel'%self.bias_assoc]
        rs.analysis = {'lock_x': self.bias[idx]}
        return rs

class RSServoSummary(servo.RampSummary):
    xlabel = 'SQ1 BIAS'

    # Override plot so we can get multiple curves in one frame.  And
    # because servo.plot is out of hand.
    
    def plot(self, plot_file=None, format=None, data_attr=None):
        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s_summary' % \
                                         (self.data_origin['basename']))
        if format is None:
            format = self.tuning.get_exp_param('tuning_plot_format',
                                               default='png')

        if data_attr is None:
            data_attr = 'y_span'
        data = self.data[data_attr]
    
        _, nrow, ncol, nbias = self.data_shape
        if self.bias_assoc == 'row':
            plot_shape = (1, nrow)
            ncurves = ncol
            data = data.reshape(nrow, ncol, nbias)
            ok = self.data['ok'].reshape(nrow, ncol, nbias)
        else:
            plot_shape = (1, ncol)
            data = data.reshape(nrow, ncol, nbias).transpose(1,0,2)
            ncurves = nrow
            ok = self.data['ok']
            
        pl = util.plotGridder(plot_shape,
                              plot_file,
                              title=self.data_origin['basename'],
                              xlabel=self.xlabel,
                              ylabel=self.ylabels[data_attr],
                              target_shape=(4,2),
                              row_labels=True,
                              format=format)
            
        an = self.analysis
        for _, r, ax in pl:
            if r >= plot_shape[1]:
                continue
            x = self.fb/1000.
            for i in xrange(ncurves):
                ax.add(biggles.Curve(x, data[r,i]/1000.))
            if 'lock_x' in an:
                ax.add(biggles.LineX(an['lock_x'][r] / 1000., type='dashed'))

        return {
            'plot_files': pl.plot_files,
            }

