import time
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
    
