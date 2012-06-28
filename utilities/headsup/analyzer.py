"""
Implement a data consumer using pylab.
"""

import time
import clients, nets, util

class dataAnalyzer(clients.dataConsumer):
    def __init__(self, name='pylab'):
        clients.dataConsumer.__init__(self, nets.default_addr, name)
        self.config = {}
    def go(self):
        if not self.connected:
            self.connect()
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
                timer.record(1)
            else:
                timer.record(0)

if __name__ == '__main__':

    pp = dataAnalyzer()
    pp.go()
    print 'disconnected.'

