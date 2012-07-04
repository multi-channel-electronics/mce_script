from PyQt4 import QtCore, QtGui
import numpy as np

from mheadsup import gfx

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
        # Expects data to be float, 0 to 1.
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


class blipColorMap:
    def __init__(self, beginColor, endColor, granularity=256):
        self.brushes = []
        def unpack_color(c):
            if isinstance(c, QtGui.QColor):
                c = c.getRgb()
            if len(c)  == 3:
                (r,g,b),a = c, 255
            else:
                r,g,b,a = c
            return r,g,b,a
        r0,g0,b0,a0 = unpack_color(beginColor)
        r1,g1,b1,a1 = unpack_color(endColor)
        def ramp_colors(a, b, n):
            return [a + (b-a)*i/(n-1) for i in range(n)]
        r = ramp_colors(r0, r1, granularity)
        g = ramp_colors(g0, g1, granularity)
        b = ramp_colors(b0, b1, granularity)
        a = ramp_colors(a0, a1, granularity)
        # Brushes.
        for row in zip(r,g,b,a):
            color = QtGui.QColor(*row)
            self.brushes.append(QtGui.QBrush(color))
    def __getitem__(self, i):
        return self.brushes[i]
    

class BlipDisplay(QtGui.QGraphicsItemGroup):
    """
    This can display plotting elements in arbitrary locations.  When
    run as a close-packed grid it should act just like a GridDisplay.
    But slower.  So it's main advantage is for non-rectangular array
    configurations.
    """
    blip_pen = QtGui.QPen(QtCore.Qt.NoPen)
    blip_brush = QtGui.QBrush(QtGui.QColor(128,128,128))
    blip_cmap = None
    data = None

    def set_data(self, data):
        if self.data == None or data.shape != self.data.shape:
            self.prepareGeometryChange()
            nrow, ncol = data.shape[:2]
            self.create_blip_grid(nrow, ncol)
        self.data = data
        self.update_blips(self.data.ravel())

    def create_blip_grid(self, nrow, ncol):
        for i in self.childItems():
            self.removeFromGroup(i)
        x, y = gfx.grid_coords(nrow, ncol)
        self.create_blips(x, y)

    def create_blips(self, x, y, w=1., h=1., form='rect', constructor=None):
        if constructor == None:
            if form == 'ellipse':
                constructor = QtGui.QGraphicsEllipseItem
            elif form == 'rect':
                constructor = QtGui.QGraphicsRectItem
            else:
                raise
        for i in range(len(x)):
            item = constructor(0., 0., w, h)
            item.setPos(x[i], y[i])
            item.setPen(self.blip_pen)
            item.setBrush(self.blip_brush)
            self.addToGroup(item)

    def update_blips(self, colors):
        if self.blip_cmap == None:
            self.blip_cmap = blipColorMap((0,0,0),(255,255,255))
        idx = (colors*255).astype('int')
        idx[idx<0] = 0
        idx[idx>255] = 255
        for c,i in zip(idx, self.childItems()):
            i.setBrush(self.blip_cmap[c])

    #
    # Virtual method implementation
    # 
    temp_bounds = None
    def boundingRect(self):
        if self.temp_bounds != None:
            return self.temp_bounds
        return QtGui.QGraphicsItemGroup.boundingRect(self)

    def mousePressEvent(self, ev):
        x0,y0,x1,y1 = self.boundingRect().getCoords()
        x, y = ev.pos().x(), ev.pos().y()
        x, y = int(np.floor(x-x0)), int(np.floor(y-y0))
        self.last_click = x, y

    # This is dumb.
    def animateMove(self, new_x=None, new_y=None, t=1.):
        self._anim_data = {
            'old_pos': ([i.pos().x() for i in self.childItems()],
                        [i.pos().y() for i in self.childItems()]),
            'new_pos': (new_x, new_y),
            'step': 0,
            'n_step': 100,
            'timer': None
            }
        timer = QtCore.QTimer()
        self._anim_data['timer'] = timer
        timer.timeout.connect(self._anim)
        x0,x1,y0,y1 = new_x.min()-2, new_x.max()+2, new_y.min()-2, new_y.max()-2
        self.prepareGeometryChange()
        self.temp_bounds = self.mapRectToScene(QtCore.QRectF(x0,y0,x1-x0,y1-y0))
        timer.start(t / self._anim_data['n_step'])
    
    def _anim(self):
        ad = self._anim_data
        ad['step'] += 1
        x0, y0 = ad['old_pos']
        x1, y1 = ad['new_pos']
        s, n = ad['step'], ad['n_step']
        for i, item in enumerate(self.childItems()):
            x, y = (x1[i]-x0[i])*s/n + x0[i], (y1[i]-y0[i])*s/n + y0[i]
            item.setPos(x, y)
        if s == n:
            self.prepareGeometryChange()
            self.temp_bounds = None
            del ad['timer']

if __name__ == '__main__':
    app = QtGui.QApplication([])

    view = tightView()
    view.setScene(QtGui.QGraphicsScene())
    view.show()
