# vim: ts=4 sw=4 et
import os
import biggles
import auto_setup.util as util
from numpy import *
import numpy as np

import servo


class CSServo(servo.SquidData):
    """
    Chip-select servo analysis for two-level mux11d addressing.

    Analyzes a chip-select flux sweep where AC2 on_bias is ramped while
    AC row selects are deselected.  Raw data has shape (n_flux, n_rows,
    n_cols); rows are grouped by their AC2 address (chip) and averaged
    to produce (n_flux, n_chips, n_cols).  Finds on/off bias levels per
    chip, analogous to how RSServo finds row select/deselect.
    """
    stage_name = 'CSServo'
    xlabel = 'CS flux / 1000'
    ylabels = {'data': 'SA FB / 1000'}
    bias_assoc = 'col'

    def __init__(self, data=None, fb=None, ac2_row_order=None,
                 tuning=None, origin='csservo'):
        servo.SquidData.__init__(self, tuning=tuning)
        self.super_servo = False
        self.chip_addrs = None
        self.n_chips = 0
        if data is not None:
            self._load(data, fb, ac2_row_order, origin)

    def _load(self, data, fb, ac2_row_order, origin):
        """
        data: array of shape (n_flux, n_rows, n_cols) -- raw SA FB at
              each flux step, for all muxed rows.
        fb:   1-d array of flux values, length n_flux.
        ac2_row_order: array of length n_rows giving the AC2 address
                       for each row visit.
        """
        n_flux, n_rows, n_cols = data.shape
        ac2_row_order = np.asarray(ac2_row_order)
        self.chip_addrs = sorted(set(ac2_row_order))
        self.n_chips = len(self.chip_addrs)

        # Average over row visits that share the same chip address.
        chip_data = np.zeros((n_flux, self.n_chips, n_cols), dtype='float')
        for ci, addr in enumerate(self.chip_addrs):
            mask = (ac2_row_order == addr)
            chip_data[:, ci, :] = data[:, mask, :].mean(axis=1)

        # Transpose to (n_chips, n_cols, n_flux) then flatten leading
        # dims so SquidData sees shape (-1, n_fb).
        self.data_shape = (self.n_chips, n_cols, n_flux)
        self.data = chip_data.transpose(1, 2, 0)  # (n_chips, n_cols, n_flux)
        self.data = self.data.reshape(-1, n_flux)

        self.fb = fb
        self.d_fb = fb[1] - fb[0] if len(fb) > 1 else 1
        self.bias_style = 'select'
        self.bias = np.zeros(n_cols, 'int')
        self.cols = np.arange(n_cols)
        self.rows = np.arange(self.n_chips)
        self.gridded = True
        self.mcefile = None
        self.rf = None
        self.data_origin = {'filename': origin, 'basename': origin}

    def reduce(self, slope=None):
        self._check_data()
        self._check_analysis(existence=True)

        n_chip, n_col, n_fb = self.data_shape
        curves = self.data.reshape(n_chip, n_col, n_fb)

        sel_idx = np.zeros((n_chip, n_col), dtype='int')
        desel_idx = np.zeros((n_chip, n_col), dtype='int')
        ok = np.zeros((n_chip, n_col), dtype='bool')

        for ci in range(n_chip):
            for co in range(n_col):
                y = curves[ci, co]
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

        # Convert to flux values
        cs_on_bias = self.fb[sel_idx_chip]
        cs_off_bias = self.fb[desel_idx_chip]

        self.analysis['cs_on_bias'] = cs_on_bias
        self.analysis['cs_off_bias'] = cs_off_bias
        self.analysis['left_x'] = self.fb[self.analysis['desel_idx']]
        self.analysis['right_x'] = self.fb[self.analysis['sel_idx']]

        return self.analysis

    def plot(self, plot_file=None, format=None):
        if plot_file is None:
            plot_file = os.path.join(self.tuning.plot_dir, '%s' %
                                     self.data_origin['basename'])
        if format is None:
            format = self.tuning.get_exp_param('tuning_plot_format')

        self._check_data()
        self._check_analysis()

        n_chip, n_col = self.data_shape[:2]
        insets = []
        for ci in range(n_chip):
            for co in range(n_col):
                insets.append('CS=%d' % self.chip_addrs[ci])

        return servo.plot(
            self.fb, self.data, (n_chip, n_col),
            self.analysis, plot_file,
            lock_levels=False,
            intervals=True,
            insets=insets,
            title=self.data_origin['basename'],
            xlabel=self.xlabel,
            ylabel=self.ylabels['data'],
            format=format,
        )
