from numpy import *

from mce import mce

def dump_timing(m, verbose=True):
    cp = [('cc', 'num_rows'), ('cc', 'row_len'), ('cc', 'data_rate'),
          ('cc', 'num_rows_reported'), ('cc', 'num_cols_reported'),
          ('rca', 'num_rows_reported'), ('rca', 'num_cols_reported'),
          ]
    nr, rl, dr, rows_cc, cols_cc, rows_rc, cols_rc = \
              tuple([m.read(c,p)[0] for c, p in cp])
    
    f_mux = 5.e7 / nr / rl
    f_ro = f_mux / dr
    size_mux = rows_rc * cols_rc
    size_ro = rows_cc * cols_cc

    print 'Rows muxed:          %9i' % nr
    print 'RxC stored:          %i x %i = %i' % (rows_rc, cols_rc, size_mux)
    print 'Mux freq (kHz):      %9.2f' % (f_mux / 1e3)
    print 'Decimation:          %9i' % dr
    print 'Readout freq (kHz):  %9.2f' % (f_ro / 1e3)
    print 'Readout MB/s/RC:     %9.2f' % (4. * f_ro * size_ro / 1.e6)
    print 'Readout words:       %9i' % (rows_cc * cols_cc)
    print 'Match?               %9i' % (size_ro == size_mux * dr)

m = mce()
dump_timing(m)

