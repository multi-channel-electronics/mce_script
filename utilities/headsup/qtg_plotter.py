import sys, os

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

import clients, util

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
    def poll(self):
        if not self.connected:
            self.connect()
        op, _ = self.process()
        if op == 'control':
            pass
        elif op == 'data':
            dims = [self.controls.get(k,0) for k in ['nrow', 'ncol']]
            if dims[0]*dims[1] == 0:
                return
            data = self.data.pop(0).reshape(*dims).transpose()
            set_data(data)

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    opts, args = o.parse_args(defaults=defaults)

    pp = qtgPlotter(opts.server, opts.name)

    # update image data every 20ms (or so)
    t = QtCore.QTimer()
    t.timeout.connect(pp.poll)
    t.start(20)

    ## Start Qt event loop unless running in interactive mode.
    if sys.flags.interactive != 1:
        app.exec_()
