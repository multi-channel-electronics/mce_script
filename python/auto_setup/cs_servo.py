# vim: ts=4 sw=4 et
import os
import biggles
import auto_setup.util as util
from numpy import *
import numpy as np
from mce_data import MCERunfile, MCEFile

import servo


class CSServo(servo.SquidData):
    """
    Chip-select servo analysis for two-level mux11d addressing.

    Loads a .bias file produced by the cs_servo C binary, which sweeps
    ac2 on_bias while servoing SA FB, optionally repeating the sweep
    over a series of sq1_bias values (cs_servo_bias_ramp).  Raw data
    has shape (n_bias, n_rows, n_cols, n_flux); rows are grouped by
    their AC2 address (chip) and averaged to produce per-chip curves
    for analysis.
    """
    stage_name = 'CSServo'
    xlabel = 'CS flux / 1000'
    ylabels = {'data': 'SA FB / 1000',
               'error': 'Error / 1000'}
    bias_assoc = 'col'

    def __init__(self, filename=None, tuning=None):
        if tuning is None and filename is not None:
            srcdir = os.path.split(filename)[0]
            tuning = os.path.join(srcdir, 'experiment.cfg')
            if not os.path.exists(tuning):
                tuning = None
        servo.SquidData.__init__(self, tuning=tuning)
        self.super_servo = None
        self.data_attrs.append('error')
        self.chip_addrs = None
        self.n_chips = 0
        self.chip_data = None
        self.chip_error = None
        if filename is not None:
            self.read_data(filename)

    def read_data(self, filename):
        rf = MCERunfile(filename+'.run')
        self.rf = rf
        self.data_origin = {'filename': filename,
                            'basename': filename.split('/')[-1]}

        # loop1 is the (optional) sq1 bias ramp; loop2 is the chip
        # select flux sweep.
        self.load_ramp_params('RB sq1 bias')
        if self.bias_style == 'select':
            self.bias_assoc = 'col'

        self.data_shape = (len(self.bias), 1, len(self.cols), len(self.fb))
        self._read_super_bias(filename)

    def _group_by_chip(self):
        """
        Average data across row visits that share the same AC2 address.
        Stores chip_data and chip_error with shape (n_chips, n_cols, n_flux).
        """
        if self.chip_data is not None:
            return

        ac2_row_order = np.asarray(
            self.tuning.get_exp_param('ac2_row_order'))
        self.chip_addrs = sorted(set(ac2_row_order))
        self.n_chips = len(self.chip_addrs)

        # data_shape is (n_row, n_col, n_fb) for single-bias data, or
        # (n_bias, n_row, n_col, n_fb) for an un-collapsed bias ramp
        # (see mux11d.do_cs_servo, which collapses ramps via
        # select_biases() before analysis, so n_bias is always 1 here).
        n_row, n_col, n_fb = self.data_shape[-3:]
        n_bias = self.data_shape[0] if len(self.data_shape) == 4 else 1
        if n_bias != 1:
            raise RuntimeError(
                'cs_servo bias ramp data must be collapsed with '
                'select_biases() before analysis.')

        # ac2_row_order has one entry per chip select; the acquired data
        # has one entry per physical row, with each chip's rows forming a
        # contiguous block of ac_num_rows rows, so expand ac2_row_order to
        # match.
        rows_per_chip = self.tuning.get_exp_param('ac_num_rows')
        if rows_per_chip * len(ac2_row_order) != n_row:
            raise RuntimeError(
                'ac_num_rows (%d) * len(ac2_row_order) (%d) = %d does not '
                'match the acquired row count (%d); check experiment.cfg.'
                % (rows_per_chip, len(ac2_row_order),
                   rows_per_chip * len(ac2_row_order), n_row))
        row_chip_map = np.repeat(ac2_row_order, rows_per_chip)

        chip_avg = np.zeros((self.n_chips, n_col, n_fb), dtype='float')
        chip_err = np.zeros((self.n_chips, n_col, n_fb), dtype='float')

        for src, dst in [(self.data, chip_avg), (self.error, chip_err)]:
            raw = src.reshape(n_row, n_col, n_fb)
            for ci, addr in enumerate(self.chip_addrs):
                mask = (row_chip_map == addr)
                dst[ci] = raw[mask].mean(axis=0)

        self.chip_data = chip_avg
        self.chip_error = chip_err

    def reduce(self, slope=None):
        self._check_data()
        self._check_analysis(existence=True)
        self._group_by_chip()

        n_chip, n_col, n_fb = self.chip_data.shape

        sel_idx = np.zeros((n_chip, n_col), dtype='int')
        desel_idx = np.zeros((n_chip, n_col), dtype='int')
        ok = np.zeros((n_chip, n_col), dtype='bool')

        for ci in range(n_chip):
            for co in range(n_col):
                y = self.chip_data[ci, co]
                reg = servo.get_curve_regions(y, extrema=True)
                lo, hi = None, None
                r = list(reg)
                while len(r) > 0:
                    if r[1][1] > r[1][0]:
                        lo = r[1]
                        break
                    r = r[2:]
                if lo and len(r) >= 3:
                    hi = r[2]
                if lo and hi:
                    span = abs(y[hi[0]:hi[1]].max() - y[lo[0]:lo[1]].min())
                    if span > 500:
                        ok[ci, co] = True
                        desel_idx[ci, co] = np.argmin(y[lo[0]:lo[1]]) + lo[0]
                        sel_idx[ci, co] = np.argmax(y[hi[0]:hi[1]]) + hi[0]

        # Per-chip: median across OK columns
        sel_idx_chip = np.zeros(n_chip, dtype='int')
        desel_idx_chip = np.zeros(n_chip, dtype='int')
        for ci in range(n_chip):
            if any(ok[ci]):
                sel_idx_chip[ci] = int(np.median(sel_idx[ci, ok[ci]]))
                desel_idx_chip[ci] = int(np.median(desel_idx[ci, ok[ci]]))

        self.analysis['sel_idx'] = sel_idx.ravel()
        self.analysis['desel_idx'] = desel_idx.ravel()
        self.analysis['ok'] = ok.ravel()
        self.analysis['sel_idx_chip'] = sel_idx_chip
        self.analysis['desel_idx_chip'] = desel_idx_chip

        cs_on_bias = self.fb[sel_idx_chip]
        cs_off_bias = self.fb[desel_idx_chip]

        self.analysis['cs_on_bias'] = cs_on_bias
        self.analysis['cs_off_bias'] = cs_off_bias
        self.analysis['left_x'] = self.fb[self.analysis['desel_idx']]
        self.analysis['right_x'] = self.fb[self.analysis['sel_idx']]

        return self.analysis

    def plot(self, plot_file=None, format=None, data_attr='data'):
        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' %
                                     self.data_origin['basename'])
        if format is None:
            format = self.tuning.get_exp_param('tuning_plot_format')

        # Multi-bias ramp: split into one single-bias CSServo per bias
        # index and plot each (mirrors SquidData.plot's ramp handling).
        if self.bias_style == 'ramp':
            ss = self._get_ramp_splits()
            plot_files = []
            for i, s in enumerate(ss):
                p = s.plot(plot_file=plot_file+'_b%02i'%i, format=format,
                           data_attr=data_attr)
                plot_files += p['plot_files']
            return {'plot_files': plot_files}

        self._check_data()
        self._check_analysis()
        self._group_by_chip()

        n_chip, n_col = self.chip_data.shape[:2]

        # Select data or error for plotting
        if data_attr == 'error':
            source = self.chip_error
        else:
            source = self.chip_data

        # Flatten to (n_chip*n_col, n_fb) for servo.plot
        plot_data = source.reshape(-1, source.shape[-1])

        
        idx = np.arange(n_chip)
        insets = ['BIAS = %5i' % b for b in self.bias]
        ## then repeat it as needed
        insets = np.concatenate([insets for i in idx])

        insets2 = []
        for ci in range(n_chip):
            for co in range(n_col):
                insets2.append('CS=%d' % self.chip_addrs[ci])

        return servo.plot(
            self.fb, plot_data, (n_chip, n_col),
            self.analysis, plot_file,
            lock_levels=False,
            intervals=data_attr != 'error',
            insets=insets,
            insets2=insets2,
            title=self.data_origin['basename'],
            xlabel=self.xlabel,
            ylabel=self.ylabels[data_attr],
            label_style='chip_col',
            format=format,
        )

    def plot_error(self, *args, **kwargs):
        if not 'data_attr' in kwargs:
            kwargs['data_attr'] = 'error'
        if not 'plot_file' in kwargs:
            kwargs['plot_file'] = os.path.join(self.tuning.plot_dir, '%s' % \
                                  (self.data_origin['basename'] + '_err'))
        return self.plot(*args, **kwargs)
