import os, sys, time
import numpy as np
import subprocess
from optparse import OptionParser


"""
Configuration is provided through a config file, which may be
overridden to various degrees from the command line.
"""

defaults = {
    'client_name': 'flatfile',
    'host': 'localhost',
    'port': 12354,
    'tunnel': None,
    'mcefile': '/data/cryo/flatfile',
    'host_var': 'MHU_SERVER',
    'config_file': '/etc/mheadsup/main.cfg',
    }

_defaults = defaults

import ConfigParser as cp
class MainConfig(cp.ConfigParser):
    filename = _defaults['config_file']

    def __init__(self, filename=None):
        cp.ConfigParser.__init__(self)
        if filename != None:
            self.filename = filename
        if not os.path.exists(self.filename):
            print 'Config file %s not found' % self.filename
        else:
            self.read(self.filename)

    def get_with_default(self, section, key, default=None):
        try:
            cp.ConfigParser.get(self, section, key)
        except cp.NoOptionError:
            return default
        
    def get_server_config(self, key=None):
        if not 'Servers' in self.sections():
            return {}
        if key == None:
            key = self.get('Servers', 'default_server')
        server_list = [x.split() for x in
                       self.get('Servers', 'server_list').split('\n')]
        keys, filenames = zip(*[w for w in server_list if len(w) != 0])
        filename = filenames[keys.index(key)]
        if filename[0] != '/':
            filename = os.path.join(os.path.split(self.filename)[0], filename)
        scfg = cp.ConfigParser()
        scfg.read(filename)
        if key in scfg.sections():
            data = dict(scfg.items(key))
            if 'port' in data:
                data['port'] = int(data['port'])
            if 'tunnel' in data and data['tunnel'] == '':
                data['tunnel'] = None
            return data
        return {}


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
            target['host'] = host_port[0]
        if len(host_port) > 1 and host_port[1] != '':
            target['port'] = int(host_port[1])
    return target

class upOptionParser(OptionParser):
    def add_standard(self, defaults=_defaults):
        self.add_option('--config-file',
                        default=defaults['config_file'])
        self.add_option('--name',
                         default=defaults['client_name'])
        self.add_option('--server',default=None)
        self.add_option('--host', default=None)
        self.add_option('--port', default=None)
        self.add_option('--port-file', default=None)

    def parse_args(self, defaults=None):
        opts, args = OptionParser.parse_args(self)
        if opts.config_file != None:
            cfg = MainConfig(opts.config_file)
            self.server_cfg = defaults.copy()
            self.server_cfg.update(cfg.get_server_config(opts.server))
            if opts.port == None:
                opts.port = self.server_cfg['port']
            if opts.host == None:
                opts.host = self.server_cfg['host']
            if hasattr(opts, 'tunnel') and opts.tunnel == None:
                opts.tunnel = self.server_cfg['tunnel']
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

