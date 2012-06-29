"""
Watch an MCE flatfile for new data, send it out.
"""

import clients, util
import mce_data

import threading
import time
import os

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'flatfile',
    'mcefile': '/data/cryo/flatfile',
    'threaded': False,
    })


class mceFileFollower(clients.dataProducer):
    def __init__(self, addr, name='flatfile', field=None):
        clients.dataProducer.__init__(self, addr, name)
        self.dshape = None
        self.delay = .03
        self.options = {'delay': .03,
                        'step': 10,
                        'watch': .1,
                        'field': field,
                        'active': False,
                        'looping': False,
                        'exit': False,
                        'filename': None,
                        'reinit': False,
                        }
        self.threads = {}
    def cleanup(self):
        expires = time.time() + 2.
        while True:
            ok = True
            for t in self.threads:
                if t.is_alive():
                    ok = False
                    self.options['exit'] = True
            if ok:
                break
            if time.time() > expires:
                print 'Orphaned threads would not die.'
                break
            time.sleep(.1)

    def _check_thread(self, active=False):
        if self.options['exit']:
            return False
        tt = threading.current_thread()
        if tt in self.threads:
            return self.threads[tt]
        return True
        
    def go(self, background=True):
        if background:
            tt = threading.Thread(target=self.go, kwargs={'background':False})
            self.threads[tt] = True
            tt.start()
            return tt
        opts = self.options
        while self._check_thread():
            opts['looping'] = True
            opts['reinit'] = False
            filename = opts['filename']
            if not opts['active'] or \
                    filename == None or \
                    not os.path.exists(filename):
                time.sleep(opts['watch']*5)
                continue
            f = mce_data.MCEFile(filename)
            self.mcefile = f
            n = 0
            while self._check_thread() and not opts['reinit']:
                dn = opts['step']
                while f.n_frames - n < dn:
                    time.sleep(opts['watch'])
                    f._UpdateNFrames()
                    if dn < f.n_frames < n:
                        # new file!
                        n = 0
                        break
                d = f.Read(start=n, count=dn, row_col=True,
                           field=opts['field'])
                self.post_data(d.data[...,-1])
                n += dn
                time.sleep(opts['delay'])
                
        opts['looping'] = False
        self.threads.pop(threading.current_thread())
            
    def playback(self, filename, background=False):
        if not os.path.exists(filename):
            print 'Warning: file "%s" does not exist, but we will wait for it.' % \
                filename
        if not background:
            self.cleanup()
            self.options['exit'] = False
        self.options['filename'] = filename
        self.options['active'] = True
        if background and self.options['looping']:
            self.options['reinit'] = True
        else:
            self.go(background=background)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_option('--data-field')
    #o.add_option('--plot', action='store_true')
    #o.add_option('--plotter', default='pylab')
    o.add_option('--zlims', type=float, nargs=2)
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults)
    
    if len(args) > 0:
        flatfile = args[0]
    else:
        flatfile = defaults['mcefile']

    mp = mceFileFollower(opts.server, opts.name,
                         field=opts.data_field)
    if opts.zlims:
        mp.send_control('zmin', opts.zlims[0])
        mp.send_control('zmax', opts.zlims[1])
    mp.playback(flatfile, background=defaults['threaded'])

