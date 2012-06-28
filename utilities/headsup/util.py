import time


class rateTracker:
    def __init__(self):
        self.t0 = time.time()
        self.n = 0
    def record(self):
        self.n += 1
        t1 = time.time()
        dt = t1 - self.t0
        if dt  > 4:
            print 'Frames per sec: %6.3f' % (self.n / dt)
            self.n = 0
            self.t0 = t1

