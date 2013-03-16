from PyQt4 import QtCore, QtGui
import numpy as np

from mheadsup import gfx

#
# Useful widgets
#

class simpleCombo(QtGui.QComboBox):
    private_data = None
    def __init__(self, labels=None, items=None):
        self.private_data = []
        QtGui.QComboBox.__init__(self)
        self.set_items(labels=labels, items=items)
    def get_item(self, index):
        return self.private_data[index][1]
    def set_items(self, labels=None, items=None, selection=None):
        self.clear()
        self.private_data = []
        if labels != None:
            for v in labels:
                self.addItem(QtCore.QString(v))
                self.private_data.append((v,v))
        if items != None:
            for k, v in items:
                self.addItem(QtCore.QString(v))
                self.private_data.append((v,k))
        if selection != None:
            self.setCurrentIndex(selection)
    def update_items(self, labels=None, items=None):
        """
        Update the items with as little disruption as possible.

        When items are passed, data will be updated even if label is the same.
        """
        current_names = [p[0] for p in self.private_data]
        keepers = [False for i in range(len(current_names))]
        new_data = []
        if labels != None:
            for v in labels:
                if v in current_names:
                    keepers[current_names.index(v)] = True
                else:
                    new_data.append((v,v))
        if items != None:
            for k, v in items:
                if v in current_names:
                    idx = current_names.index(v)
                    keepers[idx] = True
                    private_data[idx] = k
                else:
                    new_data.append((k,v))
        # Remove dead items
        for i in reversed([i for i,ok in enumerate(keepers) if not ok]):
            self.removeItem(i)
            self.private_data.pop(i)
        # Append new items
        for d in new_data:
            self.private_data.append(d)
            self.addItem(d[0])


class infoSummary(QtGui.QWidget):
    """
    Generic grid of Label: Data items.
    """
    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        self.items = {}
        self._order = []
        layout.setColumnMinimumWidth(0, 100)
        layout.setColumnMinimumWidth(0, 200)

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

    def fromTextItemList(self, pltexts):
        # Steal these
        for i in pltexts['_order']:
            t = pltexts[i]
            self.add_item(t.name, t.label)


class mutexHolder:
    def __init__(self, mutex):
        self.mutex = mutex
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        self.mutex.unlock()

    
class tightView(QtGui.QGraphicsView):
    """
    This magic keeps the items perfectly bounded in the window.
    """
    def __init__(self):
        QtGui.QGraphicsView.__init__(self)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff);
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff);

    def resizeEvent(self, ev):
        QtGui.QGraphicsView.resizeEvent(self, ev)
        self.rebound()

    def rebound(self):
        if self.scene():
            self.fitInView(self.scene().itemsBoundingRect(),
                           QtCore.Qt.KeepAspectRatio)
    
   
class GridDisplay(QtGui.QGraphicsObject):
    data = None
    last_click = None

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
    blip_brush0 = QtGui.QBrush(QtGui.QColor(128,128,128))
    blip_cmap = None
    data = None

    last_click = None

    def set_data(self, data):
        if self.data == None or data.shape != self.data.shape:
            self.prepareGeometryChange()
            nrow, ncol = data.shape[:2]
            self.create_blip_grid(nrow, ncol)
            self.scene().views()[0].rebound()
        self.data = data
        self.update_blips(self.data.ravel())

    def create_blip_grid(self, nrow, ncol):
        x, y = gfx.grid_coords(nrow, ncol)
        self.create_blips(x-x.mean(), y-y.mean())

    def create_blips(self, x, y, w=1., h=1., form='rect', constructor=None,
                     clear=True, rotation=0.):
        for i in self.childItems():
            self.removeFromGroup(i)
        if constructor == None:
            constructor = default_shapes.get(form, None)
            if constructor == None:
                print ' Unknown shape %s, using rect.' % form
                constructor = default_shapes['rect']
        for i in range(len(x)):
            item = constructor(-w/2, -h/2, w, h)
            item.setRotation((rotation+x*0)[i])
            item.setPos(x[i], y[i])
            item.setPen(self.blip_pen)
            item.setBrush(self.blip_brush0)
            self.addToGroup(item)
        self.prepareGeometryChange()
        self.scene().views()[0].rebound()

    def create_blips_from_geometry(self, geom):
        x, y = geom.coords
        form = geom.props.get('shape', 'rect')
        colormap = (0,0,0),(255,0,255) #geom.colormap()
        self.blip_cmap = blipColorMap(*colormap)
        return self.create_blips(x, y, form=form)

    def update_blips(self, colors):
        if self.blip_cmap == None:
            self.blip_cmap = blipColorMap((0,0,0),(255,255,255))
        idx = (colors*255).astype('int')
        self.cols = (colors, idx)
        idx[idx<0] = 0
        idx[idx>255] = 255
        for c,i in zip(idx, self.childItems()):
            i.setBrush(self.blip_cmap[c])

    def update_last_click(self, item):
        for i,it in enumerate(self.childItems()):
            if it == item:
                self.last_click = i
                break

    #
    # Virtual method implementation
    # 
    def boundingRect(self):
        return QtGui.QGraphicsItemGroup.boundingRect(self)

    def mousePressEvent(self, ev):
        x, y = ev.pos().x(), ev.pos().y()
        item = self.scene().itemAt(x, y)
        if item != None:
            self.update_last_click(item)

    # This is dumb.
    def animateMove(self, new_x=None, new_y=None, t=1.):
        if new_x == None or len(self.childItems()) != len(new_x):
            return
        self._anim_data = {
            'old_pos': ([i.pos().x() for i in self.childItems()],
                        [i.pos().y() for i in self.childItems()]),
            'new_pos': (new_x, new_y),
            'step': 0,
            'n_step': 40,
            'timer': None
            }
        timer = QtCore.QTimer()
        self._anim_data['timer'] = timer
        timer.timeout.connect(self._anim)
        x0,x1,y0,y1 = new_x.min()-2, new_x.max()+2, new_y.min()-2, new_y.max()-2
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
            # This should be a signal!
            del ad['timer']
            self.scene().views()[0].rebound()


#
# Shapes library...
#

"""
Triangles -- indices ab refer to up-downness and left-rightness.  So
00 and 11 are complementary triangles, but I'm not telling you what
they will actually look like.
"""

triangle_corners = [(0,0),(1,0),(1,1),(0,1)] * 2

def triangle_00(x0,y0,w,h):
    points = [QtCore.QPointF(x*w+x0,y*h+y0) for x,y in triangle_corners[0:]]
    return QtGui.QGraphicsPolygonItem(QtGui.QPolygonF(points))

def triangle_01(x0,y0,w,h):
    points = [QtCore.QPointF(x*w+x0,y*h+y0) for x,y in triangle_corners[1:]]
    return QtGui.QGraphicsPolygonItem(QtGui.QPolygonF(points))

def triangle_11(x0,y0,w,h):
    points = [QtCore.QPointF(x*w+x0,y*h+y0) for x,y in triangle_corners[2:]]
    return QtGui.QGraphicsPolygonItem(QtGui.QPolygonF(points))

def triangle_10(x0,y0,w,h):
    points = [QtCore.QPointF(x*w+x0,y*h+y0) for x,y in triangle_corners[3:]]
    return QtGui.QGraphicsPolygonItem(QtGui.QPolygonF(points))


"""
Hash of constructor-like functions for basic shapes.  Defines names of
basic shapes when specifying data display configurations.
"""

default_shapes = {
    'rect': QtGui.QGraphicsRectItem,
    'square': QtGui.QGraphicsRectItem,
    'circle': QtGui.QGraphicsEllipseItem,
    'ellipse': QtGui.QGraphicsEllipseItem,
    'triangle_00': triangle_00,
    'triangle_01': triangle_01,
    'triangle_11': triangle_10,
    'triangle_10': triangle_10,
}


if __name__ == '__main__':
    app = QtGui.QApplication([])

    view = tightView()
    view.setScene(QtGui.QGraphicsScene())
    view.show()
