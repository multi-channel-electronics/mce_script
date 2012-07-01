"""
Implement a data consumer using pylab.
"""

import time
import clients, nets, util

class dataAnalyzer(clients.dataConsumer):
    def __init__(self, addr=None, name='pylab'):
        clients.dataConsumer.__init__(self, addr, name)
        self.config = {}
    def go(self, rate=10.):
        if not self.connected:
            self.connect()
        self.set_client_var('rate', rate)
        timer = util.rateTracker(report=1.)
        while self.connected:
            op, data = self.process()
            if op == 'ctrl':
                print 'ctrl: updated_keys=', data
            elif op == 'data':
                dshape = self.controls.get('data_shape', None)
                if dshape != None:
                    data = self.data.pop(0).reshape(dshape)
                    timer.record(1)
            else:
                timer.record(0)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(util.defaults)
    opts, args = o.parse_args(util.defaults)

    pp = dataAnalyzer(opts.server)
    pp.go()
    print 'disconnected.'

