#!/usr/bin/python

import sys, os, time

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

# Text window widget
class infoSummary(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        self.items = {}
        self._order = []
        layout.setColumnMinimumWidth(0, 100)
        layout.setColumnMinimumWidth(0, 200)
    def fromTextItemList(self, pltexts):
        # Steal these
        for i in pltexts['_order']:
            t = pltexts[i]
            self.add_item(t.name, t.label)
    def set_text(self, name, text):
        if name in self.items:
            self.items[name][1].setText(text)

    def add_item(self, name, label, value=None):
        n = len(self._order)
        l1 = QtGui.QLabel(label)
        l2 = QtGui.QLabel(value)
        l2.setAlignment(QtCore.Qt.AlignRight)
        self.items[name] = (l1, l2)
        self._order.append(name)
        self.layout().addWidget(l1, n, 0)
        self.layout().addWidget(l2, n, 1)

info = infoSummary()
win.setLayout(layout)
layout.addWidget(view, 0,0)
layout.addWidget(info, 1,0)
win.show()

## Allow mouse scale/pan
#view.enableMouse()

view.setAspectLocked(True)

## Create image item
img = pg.ImageItem()
view.scene().addItem(img)


if not sys.flags.interactive:
    def sigint(signum, frame):
        app.exit()
    import signal 
    signal.signal(signal.SIGINT, sigint)


class mutexHolder:
    def __init__(self, mutex):
        self.mutex = mutex
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.mutex.unlock()

class qtgPlotter(plotters.displayClient):
    def __init__(self, addr, name='qtg'):
        plotters.displayClient.__init__(self, addr, name)
        self.img = []
        self.img_data = []
        self.mutex = QtCore.QMutex()
        # Replace label manager
        info.fromTextItemList(self.texts)
        self.texts = info

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
        if data == None or self.controls.get('data_shape', None) == None:
            return
        # Update zoom to match image?
        if self.last_data == None or self.last_data.shape != data.shape:
            view.setRange(QtCore.QRectF(0, 0, data.shape[0], data.shape[1]))
        self.last_data = data
        # Update data mask?
        if self.controls.get('mask_update'):
            self.data_mask = np.array(self.controls['mask']).astype('bool')
            self.controls['mask_update'] = False
        mask = self.data_mask
        if mask == None or mask.shape != data.shape:
            mask = np.ones(data.shape, 'bool')
        if mask.sum() == 0:
            mask[0,0] = True
        # Update zrange?
        auto, black, white = self._get_scale(data[mask])
        # Update.
        mask_val = self.controls.get('mask_value', (black+white)/2)
        data[~mask] = mask_val
        img.updateImage(data, black=black, white=white)

    def poll(self):
        self.texts.set_text('time_now', '%.1f' % time.time())
        if self.controls.get('exit'):
            print 'Exiting on server request.'
            del self.timer
            self.close()
            app.exit()
        if not self.connected:
            self.connect()
            if not self.connected:
                print 'Exiting on failed reconnect.'
                app.exit()
        if self.controls.get('poll_controls'):
            self.set_client_var('poll_controls', 1)
            self.controls['poll_controls'] = 0
        if not self.mutex.tryLock():
            return
        with mutexHolder(self.mutex):
            self.idle_count += 1
            op, item = self.process()
            if op == 'ctrl':
                if 'mask' in item:
                    self.controls['mask_update'] = True
                if 'data_mode' in item:
                    self.texts.set_text('data_mode', self.controls['data_mode'])
            elif op == 'data':
                self.texts.set_text('time_frame', '%.1f' % time.time())
                dshape = self.controls.get('data_shape', None)
                if dshape == None:
                    return
                data = self.data.pop(0).reshape(dshape).transpose()
                self.update_image(data)
                if self.idle_count == 0 and self.n_frames > 10:
                    # Falling behind... change update frequency?
                    pass
                self.idle_count = 0
                self.n_frames += 1

    def launch(self, rate=10., refresh_rate=100.):
        self.refresh_rate = refresh_rate
        self.frame_rate = refresh_rate
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(20.) #1./self.refresh_rate * 1000)
        self.frame_t0 = None
        self.n_frames = 0
        self.idle_count = 0
        pp.set_client_var('rate', rate)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_option('--no-controller',action='store_true')
    o.add_option('--data-rate', type=float, default=10.,
                 help="frame rate to request from server")
    o.add_option('--display-rate', type=float, default=100.,
                 help="rate at which to update the display")
    o.add_option('--profile',
                 help="load a plotting profile file")
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults=defaults)

    pp = qtgPlotter(opts.server, opts.name)
    pp.add_image((view,img))

    pp.launch(rate=opts.data_rate, refresh_rate=opts.display_rate)

    if sys.flags.interactive == 1 and not opts.no_controller:
        disp = plotters.displayController(opts.server, opts.name+'_ctrl')
        if opts.profile != None:
            disp.restore(opts.profile)
        # Since we're so Qt
        #disp.watch_controls(enable=True)
        #disp.timer = QtCore.QTimer()
        #disp.timer.timeout.connect(disp.watch_controls)
        #disp.timer.start(200.)
    else:
        app.exec_()
        
