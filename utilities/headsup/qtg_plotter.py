import sys, os

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

import numpy as np
import clients, util, plotters

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'qtg',
    })

app = QtGui.QApplication([])

## Create window with GraphicsView widget
#win = QtGui.QMainWindow()
win = QtGui.QWidget()
win.resize(400,600)

layout = QtGui.QGridLayout()

view = pg.GraphicsView()
#view.useOpenGL(True)
#win.setCentralWidget(view)
win.setLayout(layout)
layout.addWidget(view, 0,0)
win.show()

## Allow mouse scale/pan
#view.enableMouse()

view.setAspectLocked(True)

## Create image item
img = pg.ImageItem()
view.scene().addItem(img)


class mutexHolder:
    def __init__(self, mutex):
        self.mutex = mutex
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.mutex.unlock()

class qtgPlotter(clients.dataConsumer):
    def __init__(self, addr, name='qtg'):
        clients.dataConsumer.__init__(self, addr, name)
        self.dshape = None
        self.img = []
        self.img_data = []
        self.data_mask = None
        self.mutex = QtCore.QMutex()
        self.controls.update(plotters.display_defaults)
    def add_image(self, image, image_name=None):
        self.img.append((image, image_name))
        self.img_data.append(None)
    def update_image(self, data=None, idx=0):
        """
        Updates the image, or some aspect of it (scale, zoom, ...).
        """
        (view,img), name = self.img[idx]
        if data == None:
            data = self.last_data
        else:
            self.last_data = data
        # Update zoom to match image?
        if self.dshape != data.shape:
            self.dshape = data.shape
            view.setRange(QtCore.QRectF(0, 0, self.dshape[0], self.dshape[1]))
        # Update data mask?
        if self.controls.get('mask_update'):
            print 'mask update!'
            self.data_mask = np.array(self.controls['mask']).astype('bool')
            print self.data_mask.sum()
            self.controls['mask_update'] = False
        mask = self.data_mask
        if mask == None:
            mask = np.ones(data.shape, 'bool')
        if mask.sum() == 0:
            mask[0,0] = True
        # Update zrange?
        auto = self.controls.get('autoscale', False)
        black, white = self.controls.get('zrange', (None,None))
        if auto or black == None:
            black = data[mask].min()
        if auto or white == None:
            white = data[mask].max()
        # Update.
        mask_val = self.controls.get('mask_value', (black+white)/2)
        data[~mask] = mask_val
        img.updateImage(data, black=black, white=white)

    def poll(self):
        if self.controls.get('exit'):
            print 'Exiting on server request.'
            del self.timer
            app.exit()
        if not self.connected:
            self.connect()
            if not self.connected:
                print 'Exiting on failed reconnect.'
                app.exit()
        if not self.mutex.tryLock():
            return
        with mutexHolder(self.mutex):
            self.idle_count += 1
            op, item = self.process()
            if op == 'ctrl':
                if 'mask' in item:
                    self.controls['mask_update'] = True
            elif op == 'data':
                dshape = self.controls.get('data_shape', None)
                if dshape == None:
                    return
                data = self.data.pop(0).reshape(dshape).transpose()
                self.update_image(data)
                if self.idle_count == 0 and self.n_frames > 10:
                    # consider changing update frequency
                    pass
                self.idle_count = 0
                self.n_frames += 1

    def launch(self, refresh_rate=100.):
        self.refresh_rate = refresh_rate
        self.frame_rate = refresh_rate
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(20.) #1./self.refresh_rate * 1000)
        self.frame_t0 = None
        self.n_frames = 0
        self.idle_count = 0

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_option('--no-controller',action='store_true')
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults=defaults)

    pp = qtgPlotter(opts.server, opts.name)
    pp.add_image((view,img))
    pp.set_client_var('rate', 1000.)

    pp.launch()

    if sys.flags.interactive == 1:
        disp = plotters.displayController(opts.server, opts.name+'_ctrl')
    else:
        app.exec_()
        
