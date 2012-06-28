"""
Watch an MCE flatfile for new data, send it out.
"""

import clients, util
import mce_data
import time
import os

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'flatfile',
    'mcefile': '/data/cryo/flatfile',
    })


class mceFollower(clients.dataProducer):
    def __init__(self, addr, name='flatfile'):
        clients.dataProducer.__init__(self, addr, name)
        self.dshape = None
        self.delay = .03
        self.options = {'delay': .03,
                        'step': 10,
                        'watch': .1}
    def playback(self, filename):
        while True:
            # New file?
            while not os.path.exists(filename):
                time.sleep(1)
                continue
            f = mce_data.MCEFile(filename)
            self.f = f
            n = 0
            while True:
                dn = self.options['step']
                while f.n_frames - n < dn:
                    time.sleep(self.options['watch'])
                    f._UpdateNFrames()
                    if dn < f.n_frames < n:
                        # new file!
                        n = 0
                        break
                d = f.Read(start=n, count=dn, row_col=True)
                self.post_data(d.data[...,-1])
                n += dn
                time.sleep(self.options['delay'])

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults)
    
    if len(args) > 0:
        flatfile = args[0]
    else:
        flatfile = defaults['mcefile']

    mp = mceFollower(opts.server, opts.name)
    mp.playback(flatfile)
    

