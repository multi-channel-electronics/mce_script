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
    def __init__(self, addr, name='mce', field=None):
        clients.dataProducer.__init__(self, addr, name)
        self.mce = pymce.MCE()
        self.dshape = None
        self.delay = .03
        self.field = field
    def tick(self):
        d = self.mce.read_data(1, row_col=True)
        if self.field != None:
            d = d.extract(self.field)[:,:,0]
        else:
            d = d.data[:,:,0]
        if self.dshape != d.shape:
            self.post_meta({'data_shape': d.shape})
        self.post_data(d)
    def run(self):
        t = util.rateTracker()
        while True:
            t.record(1)
            self.tick()
            time.sleep(self.delay)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    o.add_option('--run',action='store_true')
    o.add_option('--frame-delay',type='float')
    o.add_option('--data-field')
    opts, args = o.parse_args(defaults=defaults)
    
    mp = mceProducer(opts.server, opts.name, field=opts.data_field)
    if opts.frame_delay != None:
        mp.delay = opts.frame_delay
    if opts.run:
        mp.run()
    

