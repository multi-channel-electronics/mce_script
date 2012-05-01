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


def acquire(tuning, rc, filename=None):

    # File defaults
    if filename == None:
        filename, acq_id = tuning.filename(rc=rc, action='rsservo')
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    cmd = [tuning.bin_path+'rs_servo', '-p', 50, rc, filename]

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


class RSServo(servo.SquidData):
    stage_name = 'RSServo'
    xlabel = 'SQ1 FB / 1000'
    ylabels = {'data': 'RS flux / 1000',
               'error': 'Error / 1000'}
    bias_assoc = 'rowcol'

    def __init__(self, filename=None, tuning=None):
        util.RCData.__init__(self)
        self.data_attrs.append('error')
        self.data = None
        self.analysis = None
        self.tuning = tuning
        if filename != None:
            self.read_data(filename)


    def read_data(self, filename):
        """
        Loads an sq1servo data set.  Can probably figure out if there is
        multi-row data present and do The Right Thing.
        """
        rf = MCERunfile(filename+'.run')
        self.rf = rf
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}

        # Determine columns, biases, feedbacks involved in servo
        self.load_ramp_params('RB sq1 bias')

        # Prime
        self.data_shape = (-1, 1, len(self.cols), len(self.fb))

        # Attempt load after counting bias/fb steps
        self._read_super_bias(filename)

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
            slope = slope[0]

        # Categorize curve into hi, and lo regions.
        self.reg = [servo.get_curve_regions(y*slope, extrema=True)
                    for y in self.data]
        # Identify first valley, first subsequent peak.
        pairs, oks = [], []
        for r, y in zip(self.reg, self.data*slope):
            lo, hi, ok = None, None, False
            while len(r) > 0:
                if r[1][1] > r[1][0]:
                    lo = r[1]
                    break
                r = r[2:]
            if lo and len(r) >= 3:
                hi = r[2]
            if lo and hi:
                # Watch for ramps (max->min and min->max), flat-liners.
                ok = not ((lo[0] == 0) and (hi[-1] == len(y)))
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
            self.analysis['y_span_select'] = np.argmax(span*ok,axis=0)
            # Now from those biases, identify row_sel and row_desel
            # values for each row.  Exclude failed analyses, then take
            # a median.
            sel_pair = np.zeros((2,n_row),'int')
            ok = n_ok.reshape(n_row, n_col) > 0  # ok dets
            n_ok = ok.sum(axis=1)                # n_ok dets in row
            sel = np.zeros((2, n_row))
            sel_in = self.analysis['sel_idx'].reshape(n_bias, n_row, n_col), \
                self.analysis['desel_idx'].reshape(n_bias, n_row, n_col)
            bias_idx = self.analysis['y_span_select'].reshape(n_row, n_col)
            col_idx = np.arange(n_col)
            for r in n_ok.nonzero()[0]:
                for j in [0,1]:
                    s = sel_in[j][bias_idx[r],r,col_idx]
                    sel[j, r] = np.median(s[ok[r]])
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
