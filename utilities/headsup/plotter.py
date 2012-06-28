"""
Implement a data consumer using pylab.
"""

import pylab as pl
import time

import clients, nets, util

pl.rcParams.update({
        'image.interpolation': 'nearest',
        'image.origin': 'lower'
})

class pylabPlotter(clients.dataConsumer):
    def __init__(self, name='pylab'):
        clients.dataConsumer.__init__(self, nets.default_addr, name)
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
            op, _ = self.process()
            if op == 'control':
                if self.im != None:
                    self.im = None # invalidate display
                    self.fig.clf()
            elif op == 'data':
                dims = [self.controls.get(k,0) for k in ['nrow', 'ncol']]
                if dims[0]*dims[1] == 0:
                    continue 
                data = self.data.pop(0).reshape(*dims)
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

    pp = pylabPlotter()
    pp.go()
    print 'disconnected.'
