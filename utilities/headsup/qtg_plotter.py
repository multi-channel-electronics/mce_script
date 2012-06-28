import sys, os

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

app = QtGui.QApplication([])

## Create window with GraphicsView widget
win = QtGui.QMainWindow()
win.resize(400,400)

view = pg.GraphicsView()
#view.useOpenGL(True)
win.setCentralWidget(view)
win.show()

## Allow mouse scale/pan
#view.enableMouse()

## ..But lock the aspect ratio
view.setAspectLocked(True)

## Create image item
img = pg.ImageItem()
view.scene().addItem(img)

## Set initial view bounds
view.setRange(QtCore.QRectF(0, 0, 200, 200))

idata = None
def set_data(data, rezoom=True):
    global idata
    idata = data
    if rezoom:
        dims = data.shape
        view.setRange(QtCore.QRectF(0, 0, dims[0], dims[1]))
    img.updateImage(idata, white=-2, black=2)

import time
import clients, nets, util

class qtgPlotter(clients.dataConsumer):
    def __init__(self, name='qtg'):
        clients.dataConsumer.__init__(self, nets.default_addr, name)
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
    def go(self):
        timer = util.rateTracker()
        while self.connected:
            self.poll()

if __name__ == '__main__':
    #pp = qtgPlotter()

    # update image data every 20ms (or so)
    t = QtCore.QTimer()
    #t.timeout.connect(pp.poll)
    t.start(20)

    ## Start Qt event loop unless running in interactive mode.
    if sys.flags.interactive != 1:
        app.exec_()
