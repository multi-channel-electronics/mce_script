"""
Watch an MCE flatfile for new data, send it out.
"""

import clients, nets
import mce_data
import time
import os

class mceFollower(clients.dataProducer):
    def __init__(self, name='flatfile'):
        clients.dataProducer.__init__(self, nets.default_addr, name)
        self.dshape = None
        self.delay = .03
        self.options = {'delay': .03,
                        'step': 10,
                        'watch': 1}
    def playback(self, filename):
        while True:
            # New file?
            print 'top'
            while not os.path.exists(filename):
                time.sleep(1)
                continue
            f = mce_data.MCEFile(filename)
            self.f = f
            n = 0
            print 'reader'
            while True:
                dn = self.options['step']
                while f.n_frames - n < dn:
                    time.sleep(self.options['watch'])
                    f._UpdateNFrames()
                    print '  ',f.n_frames
                    if dn < f.n_frames < n:
                        # new file!
                        n = 0
                        break
                print n
                d = f.Read(start=n, count=dn, row_col=True)
                self.post_data(d.data[...,-1])
                n += dn
                time.sleep(self.options['delay'])

if __name__ == '__main__':
    from optparse import OptionParser
    o = OptionParser()
    o.add_option('--run',action='store_true')
    opts, args = o.parse_args()
    
    SRVADR = nets.default_addr

    mp = mceFollower()
    mp.playback('/data/cryo/current_data/testfile')
    if opts.run:
        mp.run()
    

