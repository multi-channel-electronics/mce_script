"""
Implement a data consumer using pylab.
"""

import pylab as pl
import time

import clients, nets

pl.rcParams.update({
        'image.interpolation': 'nearest',
        'image.origin': 'lower'
})

class pylabPlotter(clients.dataConsumer):
    def __init__(self, name='pylab'):
        clients.dataConsumer.__init__(self, nets.default_addr, name)
        pl.ion()
        self.fig = pl.figure()
        self.config = {}
    def go(self):
        print 'initing'
        self.im = None
        self.running = True
        while self.running:
            op, data = self.process()
            if op == 'control':
                if self.im != None:
                    self.im = None # invalidate display
                    self.fig.clf()
            elif op == 'data':
                nrow, ncol = self.controls['nrow'], self.controls['ncol']
                data = self.data.pop(0).reshape(nrow, ncol)
            elif op == None:
                # Only plot when idle!  Keeps things moving...
                if self.im == None:
                    self.im = pl.imshow(data)
                else:
                    self.im.set_data(data)
                pl.draw()

if __name__ == '__main__':
    pp = pylabPlotter()
    pp.go()

