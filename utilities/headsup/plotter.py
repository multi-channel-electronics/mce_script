"""
Implement a data consumer using pylab.
"""

import pylab as pl
import time

import clients, nets, util

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'pylab',
    })

pl.rcParams.update({
        'image.interpolation': 'nearest',
        'image.origin': 'lower'
})

class pylabPlotter(clients.dataConsumer):
    def __init__(self, addr, name='pylab'):
        clients.dataConsumer.__init__(self, addr, name)
        pl.ion()
        self.fig = pl.figure()
        pl.show()
        self.config = {}
    def go(self):
        if not self.connected:
            self.connect()
        self.im = None
        self.running = True
        data = None
        timer = util.rateTracker()
        while self.connected:
            op, item = self.process()
            if op == 'control':
                if item in ['zmin','zmax']:
                    self.im.set_clim(self['zmin'], self['zmax'])
                if self.im != None:
                    self.im = None # invalidate display
                    self.fig.clf()
            elif op == 'data':
                dims = [self.controls.get(k,0) for k in ['nrow', 'ncol']]
                if dims[0]*dims[1] == 0:
                    continue 
                data = self.data.pop(0).reshape(*dims)
                if self.controls.get('zmin') == None:
                    self.controls['zmin'] = data.min()
                if self.controls.get('zmax') == None:
                    self.controls['zmax'] = data.min()
            elif op == None and data != None:
                # Only plot when idle!  Keeps things moving...
                if self.im == None:
                    self.im = pl.imshow(data)
                else:
                    self.im.set_data(data)
                pl.draw()
                timer.record()
                self._d = data
                data = None
            else:
                timer.record(0)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults=defaults)

    pp = pylabPlotter(opts.server, opts.name)
    pp.go()

