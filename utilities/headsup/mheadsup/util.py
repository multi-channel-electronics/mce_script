import os, sys, time
import numpy as np
import subprocess
from optparse import OptionParser

class rateTracker:
    def __init__(self, report=10):
        self.t0 = time.time()
        self.n = 0
        self.report = report
    def record(self, dn=1):
        self.n += dn
        t1 = time.time()
        dt = t1 - self.t0
        if dt > self.report:
            print 'Frames per sec: %6.3f' % (self.n / dt)
            self.n = 0
            self.t0 = t1

defaults = {
    'client_name': 'flatfile',
    'server_host': 'localhost',
    'server_port': 12354,
    'mcefile': '/data/cryo/flatfile',
    }

class upOptionParser(OptionParser):
    def add_standard(self, defaults):
        self.add_option('--host',
                        default=defaults['server_host'])
        self.add_option('--port', type=int,
                         default=defaults['server_port'])
        self.add_option('--name',
                         default=defaults['client_name'])

    def parse_args(self, defaults):
        opts, args = OptionParser.parse_args(self)
        opts.server = '%s:%i' % (opts.host, opts.port)
        return opts, args


def make_interactive(yes_do_it=True):
    if not sys.flags.interactive:
        # Uh, ok.
        sys.exit(subprocess.call(['/usr/bin/python','-i'] + sys.argv))

        
def get_type(x):
    if isinstance(x, int):
        return 'int'
    if isinstance(x, float):
        return 'float'
    return 'str'
    
casts = {
    'int': int,
    'float': float,
    'str': str,
}

def get_type_value_pair(dtype, value):
    if dtype == None:
        dtype = get_type(value)
        return dtype, str(value)
    return dtype, value

def guess_type(x):
    try:
        int(x)
        return int
    except:
        try:
            float(x)
            return float
        except:
            return str

def load_columns(fin, cols=None, skip=0):
    if isinstance(fin, basestring):
        fin = open(fin)
    n_col = None
    for i in range(skip):
        fin.readline()
    data = []
    for line in fin:
        line = line.strip()
        if len(line) == 0 or line[0] == '#':
            continue
        w = line.split()
        if n_col == None:
            n_col = len(w)
        if cols == None:
            data.append(w)
        else:
            data.append(w[i] for i in cols)
    return [np.array(x).astype(guess_type(x[0])) for x in zip(*data)]
