#!/usr/bin/python

"""
Implement a data consumer using pylab.
"""

import pylab as pl
import numpy as np
import time
import os
import sys
import subprocess

import clients, nets, util, plotters

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'pylab',
    'mark_masked': True,
    })

pl.rcParams.update({
        'image.interpolation': 'nearest',
        'image.origin': 'upper'
})



class pylabPlotter(plotters.displayClient):
    def __init__(self, addr, name='pylab'):
        plotters.displayClient.__init__(self, addr, name)
        pl.ion()
        ax = pl.subplot2grid((1,3), (0,0),colspan=2)
        pl.show()

    def update_image(self, data=None, idx=0):
        """
        Updates the image, or some aspect of it (scale, zoom, ...).
        """
        im = self.im
        if data == None:
            data = self.last_data
        else:
            self.last_data = data
        if data == None or self.controls.get('data_shape', None) == None:
            return
        # Update zoom to match image?
        if self.last_data == None or self.last_data.shape != data.shape:
            im = None # Start over.
        # Update data mask?
        if self.controls.get('mask_update'):
            self.data_mask = np.array(self.controls['mask']).astype('bool')
            self.controls['mask_update'] = False
        mask = self.data_mask
        if mask == None:
            mask = np.ones(data.shape, 'bool')
        if mask.sum() == 0:
            mask[0,0] = True
        # Update zrange?
        auto, black, white = self._get_scale(data[mask])
        # Update.
        mask_val = self.controls.get('mask_value', (black+white)/2)
        data[~mask] = mask_val
        if im == None:
            self.im = pl.imshow(data, vmin=black, vmax=white)
        else:
            self.im.set_data(data)
            self.im.set_clim(black, white)
        pl.draw()

    def update_texts(self, redraw=None):
        ofs, dofs = .9, -.05
        n = 0
        update = False
        for i in self.texts['_order']:
            n += 1
            label, text = self.texts[i].get_update()
            if label == None:
                continue
            update = True
            if not i in self.texts['_gobj']:
                self.texts['_gobj'][i] = \
                    pl.figtext(0.8, ofs+n*dofs, '', ha='right'), \
                    pl.figtext(.97, ofs+n*dofs, '', ha='right')
            t1, t2 = self.texts['_gobj'][i]
            t1.set_text(label)
            t2.set_text(text)

        if redraw != False and update:
            pl.draw()

    def go(self, rate=10.):
        if not self.connected:
            self.connect()
        self.im = None
        self.last_data = None
        self.data_mask = None
        timer = util.rateTracker()
        self.set_client_var('rate', rate)
        if self.controls.get('poll_controls'):
            self.set_client_var('poll_controls', 1)
            self.controls['poll_controls'] = 0
        self.set_client_var('rate', rate)
        while self.connected:
            if self.controls.get('exit'):
                print 'Server issued client kill.'
                break
            op, data = self.process()
            if op == 'ctrl':
                self.update_image(None)
            elif op == 'data':
                self.texts.set_text('time_frame', '%.1f' % time.time())
                dshape = self.controls.get('data_shape', None)
                if dshape == None:
                    continue
                data = self.data.pop(0).reshape(dshape)
                self.update_image(data)
                timer.record(1)
            else:
                timer.record(0)
                time.sleep(.01)
            self.texts.set_text('time_now', '%.1f' % time.time())
            self.update_texts()

if not sys.flags.interactive:
    def sigint(signum, frame):
        sys.exit()

    import signal 
    signal.signal(signal.SIGINT, sigint)


if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    o.add_option('--no-controls',action='store_true')
    o.add_option
    opts, args = o.parse_args(defaults=defaults)

    pp = pylabPlotter(opts.server, opts.name)
    pp.go()
