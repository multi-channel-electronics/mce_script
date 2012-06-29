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
            if self.controls.get('exit'):
                print 'Server issued client kill.'
                break
            op, items = self.process()
            if op == 'ctrl':
                auto = self.controls.get('autoscale', False)
                if not auto and ('autoscale' in items or 'zrange' in items):
                    # Set the image scale to most recent zrange
                    self.im.set_clim(*self.controls['zrange'])
            elif op == 'data':
                dshape = self.controls.get('data_shape',None)
                if dshape == None:
                    continue 
                data = self.data.pop(0).reshape(dshape)
                auto = self.controls.get('autoscale', False)
                if auto:
                    self.im.set_clim(data.min(), data.max())
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

