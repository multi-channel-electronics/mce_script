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
                        'filename': None,
                        'trigger_exit': False,
                        'seek_tail': False,
                        'control_forever': True,
                        'control_active': False,
                        'status_looping': False,
                        'trigger_reinit': False,
                        }
        self.threads = {}
    def cleanup(self):
        expires = time.time() + 2.
        while True:
            ok = True
            for t in self.threads:
                if t.is_alive():
                    ok = False
                    self.options['trigger_exit'] = True
            if ok:
                break
            if time.time() > expires:
                print 'Orphaned threads would not die.'
                break
            time.sleep(.1)

    def _check_thread(self, active=False):
        if self.options['trigger_exit']:
            return False
        tt = threading.current_thread()
        if tt in self.threads:
            return self.threads[tt]
        return True
        
    def go(self, background=True):
        # For background mode, call this function again from a new thread.
        if background:
            tt = threading.Thread(target=self.go, kwargs={'background':False})
            self.threads[tt] = True
            tt.start()
            return tt
        opts = self.options
        # Main file watch loop
        while self._check_thread():
            # Inform everyone that we made it to the top
            opts['status_looping'] = True
            # Clear the reinit trigger
            opts['trigger_reinit'] = False
            # Are we idle / aimless?
            filename = opts['filename']
            if not opts['control_active'] or \
                    filename == None or \
                    not os.path.exists(filename):
                if opts['watch'] == None:
                    break
                time.sleep(opts['watch'] * 5)
                continue
            # We appear to have some data to process.
            f = mce_data.MCEFile(filename)
            self.mcefile = f
            if opts['seek_tail']:
                # Go to almost end
                n = min(f.n_frames - dn, 0)
            else:
                # Start from beginning
                n = 0
            # Frame reader loop
            while self._check_thread() and not opts['trigger_reinit']:
                dn = opts['step']
                while f.n_frames - n < dn:
                    if opts['watch'] == False:
                        # This is for playback-and-exit mode.
                        n = -1
                        break
                    time.sleep(opts['watch'])
                    f._UpdateNFrames()
                    if dn < f.n_frames < n:
                        # A sign that the file has been reset; do reinit
                        n = -1
                        break
                if n == -1:
                    break
                d = f.Read(start=n, count=dn, row_col=True,
                           field=opts['field'])
                self.post_data(d.data[...,-1])
                n += dn
                time.sleep(opts['delay'])
            # Try again?
            if not opts['control_forever']:
                break
        # Cleanup
        opts['status_looping'] = False
        tt = threading.current_thread()
        if tt in self.threads:
            self.threads.pop(tt)
            
    def playback(self, filename, background=False):
        if not os.path.exists(filename):
            print 'Warning: file "%s" does not exist, but we will wait for it.' % \
                filename
        if not background:
            self.cleanup()
            self.options['trigger_exit'] = False
        self.options['filename'] = filename
        self.options['control_active'] = True
        if background and self.options['status_looping']:
            self.options['trigger_reinit'] = True
        else:
            self.go(background=background)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_option('--data-field')
    o.add_option('--once', action='store_true')
    o.add_option('--loop', action='store_true')
    o.add_option('--zlims', type=float, nargs=2)
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults)

    if len(args) > 0:
        flatfile = args[0]
    else:
        flatfile = defaults['mcefile']

    mp = mceFileFollower(opts.server, opts.name,
                         field=opts.data_field)

    if opts.once:
        mp.options['control_forever'] = False
        mp.options['watch'] = False
    
    if opts.zlims:
        mp.post_meta({'zrange': opts.zlims})

    while True:
        mp.playback(flatfile, background=defaults['threaded'])
        if not opts.loop:
            break
    

