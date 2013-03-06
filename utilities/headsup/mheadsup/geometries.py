import numpy as np

"""
Classes describing layouts and shape of picture elements.

Also tracking of multiple layouts, encoding, decoding...
"""

from encoders import arrayInfoEncoder as aie

class pixelSetGeometry(aie):
    """
    Record positions of a set of pixels.
    """
    arrayInfo_simple= ['name', 'n_pix', 'n_dim', 'data_shape', 'props']
    arrayInfo_arrays = ['coords']

    def __init__(self, name='geom', shape=None):
        if shape == None:
            shape = (0,)
        self.data_shape = shape
        self.n_dim = len(shape)
        self.n_pix = 1
        for s in shape:
            self.n_pix *= s
        self.coords = np.zeros(self.data_shape)
        self.name = name
        self.props = {}

    def get_coords(self, idx=None, dims=None):
        """
        Return the pixel positions.
        """
        if dims == None:
            dims = [i for i in range(self.n_dim)]
        if idx == None:
            return self.coords[dims]
        return self.coords[dims][:,idx]

    """
    Load from files
    """
    
    @classmethod
    def from_ascii_columns(cls, filename, name='file_geom',
                           columns={'x': 0, 'y': 1}):
        casts = {'x': float, 'y': float}
        data = []
        for k in casts.keys():
            if k in columns:
                data.append((k, columns[k], casts[k], []))
        
        for line in open(filename):
            w = line.split()
            if len(w) == 0 or w[0][0] == '#':
                continue
            for k, col, cst, d in data:
                d.append(cst(w[col]))
        vectors = {}
        for k, _,_, d in data:
             vectors[k] = np.array(d)
        self = cls(name=name, shape=(len(vectors['x']),))
        self.coords = np.array([vectors['x'], vectors['y']])
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
        self.coords = np.array([(x+y*0).ravel(),(y+x*0).ravel()])
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
        self.coords = np.array([radius*np.cos(theta), radius*np.sin(theta)])
        self.name = name
        return self
