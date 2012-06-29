import sys, os

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

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

idata = None
def set_data(data, rezoom=True):
    global idata
    idata = data
    if rezoom:
        dims = data.shape
        view.setRange(QtCore.QRectF(0, 0, dims[0], dims[1]))
    white = idata.max()
    black = idata.min()
    img.updateImage(idata, white=white, black=black)


class qtgPlotter(clients.dataConsumer):
    def __init__(self, addr, name='qtg'):
        clients.dataConsumer.__init__(self, addr, name)
        self.dshape = None
        self.img = []
        self.img_data = []
    def add_image(self, image, image_name=None):
        self.img.append((image, image_name))
        self.img_data.append(None)
    def update_image(self, data, idx=0):
        (view,img), name = self.img[idx]
        dshape = data.shape
        view.setRange(QtCore.QRectF(0, 0, dshape[0], dshape[1]))
        auto = self.controls.get('autoscale', False)
        black, white = self.controls.get('zrange', (None,None))
        img.updateImage(data, autoRange=auto, black=black, white=white)

    def poll(self):
        if self.controls.get('exit'):
            print 'Exiting on server request.'
            app.exit()
        if not self.connected:
            self.connect()
            if not self.connected:
                print 'Exiting on failed reconnect.'
                app.exit()
        op, item = self.process()
        if op == 'control':
            pass
        elif op == 'data':
            dshape = self.controls.get('data_shape', None)
            if dshape == None:
                return
            data = self.data.pop(0).reshape(dshape).transpose()
            #set_data(data)
            self.update_image(data)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_option('--no-controller',action='store_true')
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults=defaults)

    pp = qtgPlotter(opts.server, opts.name)
    pp.add_image((view,img))

    # update image data every 20ms (or so)
    t = QtCore.QTimer()
    t.timeout.connect(pp.poll)
    t.start(20)

    if opts.no_controller:
        ## Start Qt event loop unless running in interactive mode.
        if sys.flags.interactive != 1:
            app.exec_()
    else:
        disp = plotters.displayController(opts.server, opts.name+'_ctrl')
        
