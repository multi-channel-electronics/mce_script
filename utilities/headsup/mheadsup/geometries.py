import numpy as np

"""
Classes describing layouts and shape of picture elements.

Also tracking of multiple layouts, encoding, decoding...
"""


class pixelSetGeometry:
    """
    Record positions of a set of pixels.
    """

    def __init__(self, name='geom', shape=None):
        if shape == None:
            shape = (0,)
        self.data_shape = shape
        self.n_dim = len(shape)
        self.n_pix = 1
        for s in shape:
            self.n_pix *= s
        self.coords = []
        self.name = name
        self.props = {}

    def get_coords(self, idx=None, dims=None):
        """
        Return the pixel positions.
        """
        if dims == None:
            dims = [i for i in range(self.n_dim)]
        return tuple([self.coords[i][idx] for i in dims])

    """
    Serialization.
    """

    def encode(self):
        data = {}
        for k in ['name', 'n_pix', 'n_dim', 'data_shape', 'props']:
            data[k] = getattr(self, k)
        data['coords'] = [map(float,x) for x in self.coords]
        return data

    @classmethod
    def decode(cls, data):
        self = cls()
        for k in ['name', 'n_pix', 'n_dim', 'data_shape', 'props']:
            setattr(self, k, data[k])
        self.coords = [np.array(c) for c in data['coords']]
        return self


    """
    Quick constructors.
    """

    @classmethod
    def for_grid(cls, n_row=0, n_col=0,
                 x=None, y=None, size=None, name=''):
        self = cls()
        self.n_pix = n_row * n_col
        self.n_dim = 2
        self.data_shape = (n_row, n_col)
        if x == None:
            x = np.arange(n_col)
        if y == None:
            y = np.arange(n_row)
        x = np.asarray(x).reshape((1,-1))
        y = np.asarray(y).reshape((-1,1))
        self.coords = [(x+y*0).ravel(),(y+x*0).ravel()]
        self.size = size
        self.name = name
        return self

    @classmethod
    def circle(cls, n_pix=0, radius=None, name=''):
        self = cls()
        self.n_pix = n_pix
        self.n_dim = 2
        self.data_shape = (n_pix, 1)
        if radius == None:
            radius = 1.2 * n_pix / 2 / np.pi
        theta = 2 * np.pi * np.arange(n_pix) / n_pix
        self.coords = [radius*np.cos(theta), radius*np.sin(theta)]
        self.name = name
        return self
