"""
Implement a data consumer using pylab.
"""

import clients, nets
import pymce
import time

class mceProducer(clients.dataProducer):
    def __init__(self, name='mce'):
        clients.dataProducer.__init__(self, nets.default_addr, name)
        self.mce = pymce.MCE()
        self.dshape = None
        self.delay = .1
    def tick(self):
        d = self.mce.read_data(1, row_col=True).data[:,:,0]
        if self.dshape != d.shape:
            self.send_control('nrow', 'int', d.shape[0])
            self.send_control('ncol', 'int', d.shape[1])
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
    from optparse import OptionParser
    o = OptionParser()
    o.add_option('--run',action='store_true')
    opts, args = o.parse_args()
    
    SRVADR = nets.default_addr

    mp = mceProducer()
    if opts.run:
        mp.run()
    

