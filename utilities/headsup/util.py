import time


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

