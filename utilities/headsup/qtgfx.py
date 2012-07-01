from PyQt4 import QtCore, QtGui
import numpy as np

class tightView(QtGui.QGraphicsView):
    """
    This magic keeps the items perfectly bounded in the window.
    """
    def resizeEvent(self, ev):
        QtGui.QGraphicsView.resizeEvent(self, ev)
        if self.scene():
            self.fitInView(self.scene().itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)

class GridDisplay(QtGui.QGraphicsObject):
    data = None
    def set_data(self, data, channel=None):
        if data.dtype != 'uint8':
            # Assume float 0 to 1
            data = np.round(data*255).astype('uint8')
        if self.data == None or data.shape != self.datav.shape:
            self.prepareGeometryChange()
            nrow, ncol = data.shape[:2]
            self.data = np.zeros((nrow,ncol,4), 'uint8')
            self.data[...,3] = 255 # alpha
            self.datav = self.data[:,:ncol,:]
        if channel == None:
            self.datav[...,:3] = data[...,None]
        else:
            self.datav[...,channel] = data
        self.update()

    #
    # Virtual method implementation
    # 
    def boundingRect(self):
        if self.data != None:
            nrow, ncol = self.datav.shape[:2]
            w, h = float(ncol), float(nrow)
        else:
            w, h = 1, 1
        return QtCore.QRectF(0,0,w,h)

    def paint(self, p, *args):
        if self.data == None:
            return
        nrow, ncol = self.datav.shape[:2]
        ## Note if you change formats you need to word-align the scan lines.
        ## That's what all this datav business is for.
        #fmt = QtGui.QImage.Format_RGB888
        fmt = QtGui.QImage.Format_ARGB32
        qi = QtGui.QImage(self.data.tostring(), ncol, nrow, fmt)
        pixmap = QtGui.QPixmap.fromImage(qi)
        self.pixmap = pixmap
        p.drawPixmap(
            self.boundingRect(),
            pixmap, 
            QtCore.QRectF(0, 0, ncol, nrow),
            )

    def mousePressEvent(self, ev):
        x0,y0,x1,y1 = self.boundingRect().getCoords()
        x, y = ev.pos().x(), ev.pos().y()
        x, y = int(np.floor(x-x0)), int(np.floor(y-y0))
        self.last_click = x, y

if __name__ == '__main__':
    app = QtGui.QApplication([])

    view = tightView()
    view.setScene(QtGui.QGraphicsScene())
    view.show()
    
