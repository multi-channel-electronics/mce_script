#!/usr/bin/python

USAGE="""%prog [options] [runfiles]

Query the MCE, or parse a runfile, to evaluate the sanity of the
rectangle mode configuration.

We take this opportunity to remind the user, again, that all readout
modes are rectangle readout modes.
"""

from numpy import *

MCE_CLOCK = 5e7 # Hz
MCE_OVERHEAD = 44

class frameConfig:
    mce_params = [ \
        ('cc_rcs',  ('cc', 'rcs_to_report_data')),
        ('cc_dec',  ('cc', 'data_rate')),
        ('cc_nmux', ('cc', 'num_rows')),
        ('cc_cmux', ('cc', 'row_len')),
        ('cc_nr',   ('cc', 'num_rows_reported')),
        ('cc_nc',   ('cc', 'num_cols_reported')),
        ('rc_nmux', ('rca', 'num_rows')),
        ('rc_cmux', ('rca', 'row_len')),
        ('rc_nr',   ('rca', 'num_rows_reported')),
        ('rc_nc',   ('rca', 'num_cols_reported')),
        ('rc_r0',   ('rca', 'readout_row_index')),
        ('rc_c0',   ('rca', 'readout_col_index')),
        # Params below this point are not summarized
        ('barrier', (None, None)),
        ('rc_fw',   ('rca', 'fw_rev')),
        ]

    def __init__(self, mce=None):
        self.mce = mce
        self.clear()

    def clear(self):
        # Initialize state to indeterminate
        self.params = {}
        for k, _ in self.mce_params:
            self.params[k] = None
        self.derive()

    def derive(self):
        """
        Evaluate state parameters to determine readout features.
        These are saved in self. and returned to the user.

        If the MCE state is not yet known, None is returned.
        """
        # Check for MCE state:
        for k, _ in self.mce_params:
            if k == 'barrier':
                continue
            if self.params[k] is None:
                return None
        # 
        d = {}
        d['f_mux'] = MCE_CLOCK / self.params['cc_cmux'] / self.params['cc_nmux']
        d['f_ro'] = d['f_mux'] / self.params['cc_dec']
        d['n_mux'] = self.params['rc_nr'] * self.params['rc_nc']
        d['n_ro'] = self.params['cc_nr'] * self.params['cc_nc']
        #
        d['contiguous'] = (d['n_mux'] * self.params['cc_dec'] == d['n_ro'])
        d['complete'] = (d['n_mux'] == d['n_ro'])
        d['bizarro'] = d['n_ro'] % d['n_mux'] != 0
        d['in_bounds'] = self.params['rc_r0'] + self.params['rc_nr'] <= \
            self.params['cc_nmux']
        #
        d['f_sam'] = d['f_ro'] * (d['n_ro'] / d['n_mux'])
        #
        d['dup_bug'] = (self.params['rc_fw'] < 0x5010007) and (
            self.params['rc_nmux']*self.params['rc_cmux'] < 230 + d['n_ro']*2)
        self.derived = d

    def report(self):
        print 'MCE configuration:'
        for k, (c,p) in self.mce_params:
            if k == 'barrier':
                break
            print ' %-8s %-30s %3i' % \
                (k, '( %s, %s ):'%(c,p), self.params[k])
        print
        print 'Framing:'
        d = self.derived
        def yn(x):
            if x: return 'yes'
            return 'no'
        print ' RC words stored per mux cycle:         %4i' % d['n_mux']
        print ' CC words per read-out frame:           %4i' % d['n_ro']
        print ' CC decimation:                         %4i' % self.params['cc_dec']
        print
        print 'Sanity summary:'
        print ' Contiguous (for high-rate readout)?    %4s' % yn(d['contiguous'])
        print ' Complete   (all-detector readout)?     %4s' % yn(d['complete'])
        print ' Bizarro    (a bad thing)?              %4s' % yn(d['bizarro'])
        print ' Bounded    (a good thing)?             %4s' % yn(d['in_bounds'])
        if d['dup_bug']:
            print ' Duplicate data bug!                    %4s' % yn(d['dup_bug'])
        print
        print 'Timing:'
        print ' Mux freq:                         %9.2f' % d['f_mux']
        print ' Mean sampling freq:               %9.2f' % d['f_sam']
        print ' Read-out freq:                    %9.2f' % d['f_ro']
        print
        print 'Data volume:'
        print ' Frame size (bytes/RC):            %9i' % \
            (4*(MCE_OVERHEAD + d['n_ro']))
        print ' Data rate (MB/s/RC):              %9.2f' % \
            (1.e-6*d['f_ro'] * 4*(MCE_OVERHEAD + d['n_ro']))
        if d['dup_bug']:
            print
            print 'Warning!! your RC firmware has the duplicate data bug;'
            print '          and this configuration will suffer from it.'
 
    def from_runfile(self, filename):
        rf = MCERunfile(filename)
        acq_cards = rf.Item('FRAMEACQ', 'RC', type='int')
        rc = 'rc%i' % acq_cards[0]
        for k, (c, p) in self.mce_params:
            if k == 'barrier':
                continue
            if c == 'rca': c = rc
            item = rf.Item('HEADER', 'RB %s %s' % (c, p), type='int')
            if item is None:
                raise RuntimeError, "Failed to find key for %s %s" % (c,p)
            self.params[k] = item[0]
        self.derive()

    def from_mce(self, mce=None):
        if mce is None:
            mce = self.mce
        for k, p in self.mce_params:
            if k == 'barrier':
                self.params[k] = 1
            else:
                self.params[k] = mce.read(p[0], p[1])[0]
        self.derive()


if __name__ == '__main__':
    import sys
    from optparse import OptionParser
    o = OptionParser()
    o.add_option('-m', '--mce',action='store_true',default=False,
                 help='Query MCE rather than parsing a runfile')
    opts, args = o.parse_args()

    if opts.mce: 
	from mce_control import MCE as mce
	if len(args) > 0:
            print 'Pass runfiles or --mce, not both!'
            sys.exit(1)
        f = frameConfig(mce=mce())
        f.from_mce()
        f.report()
    else:
	from mce_data import MCERunfile
        f = frameConfig()
        for a in args:
            f.from_runfile(a)
            f.report()
            
        
