import os, sys, time
import numpy as np
import subprocess
from optparse import OptionParser

defaults = {
    'client_name': 'flatfile',
    'server_host': 'localhost',
    'server_port': 12354,
    'mcefile': '/data/cryo/flatfile',
    'host_var': 'MHU_SERVER',
    }

_defaults = defaults

def get_defaults(target=None):
    if target == None:
        target = {}
    target.update(defaults)
    if defaults.get('host_var') and \
            os.getenv(defaults['host_var']) not in ['',None]:
        # host_var should be of the form server:port or server.
        # if server or port are trivial, they are ignored, which allows
        # one to override the default port or host independently.
        host_port = os.getenv(defaults['host_var']).split(':')
        if host_port[0] != '':
            target['server_host'] = host_port[0]
        if len(host_port) > 1 and host_port[1] != '':
            target['server_port'] = int(host_port[1])
    return target

class upOptionParser(OptionParser):
    def add_standard(self, defaults=_defaults):
        self.add_option('--host',
                        default=defaults['server_host'])
        self.add_option('--port', type=int,
                         default=defaults['server_port'])
        self.add_option('--name',
                         default=defaults['client_name'])
        self.add_option('--port-file', default=None)

    def parse_args(self, defaults=None):
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



class logger:
    def __init__(self, default_priority=0, verbosity=0,
                 prefix=''):
        self.default_priority = default_priority
        self.streams = [(sys.stdout, verbosity)]
        self.prefix = ''

    def set_verbosity(self, verbosity, stream=None):
        for i in range(len(self.streams)):
            if stream==None or i==stream:
                self.streams[i] = (s, verbosity)

    def log(self, msg, priority=None):
        if priority == None:
            priority = self.default_priority
        prefix = self.prefix + '(%i):' %(os.getpid()) + ' '*priority
        for s, v in self.streams:
            if priority <= v:
                for n in msg.split('\n'):
                    s.write(prefix+n+'\n')
    
    def __call__(self, msg, priority=None):
        return self.log(msg, priority=priority)

