"""
Read data from the MCE directly.
"""

import clients, util
import pymce
import time

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'mce',
    })

class mceProducer(clients.dataProducer):
    def __init__(self, addr, name='mce'):
        clients.dataProducer.__init__(self, addr, name)
        self.mce = pymce.MCE()
        self.dshape = None
        self.delay = .03
    def tick(self):
        d = self.mce.read_data(1, row_col=True).data[:,:,0]
        if self.dshape != d.shape:
            self.send_control('nrow', d.shape[0])
            self.send_control('ncol', d.shape[1])
        self.send_data(d.ravel())
    def run(self):
        shape_fresh = 100
        while True:
            self.tick()
            time.sleep(self.delay)
            shape_fresh -= 1
            if shape_fresh == 0:
                # Trigger shape information update
                shape_fresh = 100
                self.dshape = None

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    o.add_option('--run',action='store_true')
    opts, args = o.parse_args(defaults=defaults)
    
    mp = mceProducer(opts.server, opts.name)
    if opts.run:
        mp.run()
    

