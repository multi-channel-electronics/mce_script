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
    ac2 on_bias while servoing SA FB.  Raw data has shape (1, n_rows,
    n_cols, n_flux); rows are grouped by their AC2 address (chip) and
    averaged to produce per-chip curves for analysis.
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

        # cs_servo has no bias ramp; loop1 is inactive ("none").
        # Parse as non-ramped: feedback is in loop2.
        self.load_ramp_params('RB sq1 bias')

        self.data_shape = (-1, 1, len(self.cols), len(self.fb))
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

        n_bias, n_row, n_col, n_fb = self.data_shape

        chip_avg = np.zeros((self.n_chips, n_col, n_fb), dtype='float')
        chip_err = np.zeros((self.n_chips, n_col, n_fb), dtype='float')

        for src, dst in [(self.data, chip_avg), (self.error, chip_err)]:
            curves = src.reshape(n_bias, n_row, n_col, n_fb)
            raw = curves[0]  # (n_row, n_col, n_fb)
            for ci, addr in enumerate(self.chip_addrs):
                mask = (ac2_row_order == addr)
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

        insets = []
        for ci in range(n_chip):
            for co in range(n_col):
                insets.append('CS=%d' % self.chip_addrs[ci])

        return servo.plot(
            self.fb, plot_data, (n_chip, n_col),
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
