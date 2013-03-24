import os
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
    arrayInfo_simple= ['name', 'n_pix', 'n_dim', 'data_shape', 'props',
                       'coords', 'forms', 'rotations', 'colors']
#    arrayInfo_arrays = ['coords', 'forms', 'rotations']

    def __init__(self, name='geom', shape=None):
        if shape == None:
            shape = (0,)
        self.set_shape(shape)
        self.coords = np.zeros(self.data_shape)
        self.forms = 'square'
        self.colors = 'purple'
        self.rotations = 0.
        self.name = name
        self.props = {}

    def set_shape(self, shape):
        try:
            len(shape)
        except:
            shape = (shape,)
        self.data_shape = shape
        self.n_dim = len(shape)
        self.n_pix = 1
        for s in shape:
            self.n_pix *= s

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
    Encoding to dictionaries; mostly provided by aie.
    """

    def encode(self):
        # Condition...
        self.coords = np.asarray(self.coords, dtype='float32')
        return aie.encode(self)


    """
    Load from files
    """

    def read_ascii_columns(self, filename,
                           columns={'x': 0, 'y': 1}):
        casts = {'x': float,
                 'y': float,
                 'forms': str,
                 'rotations': float,
                 'colors': str,
                 }
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
        self.coords = np.array([vectors['x'], vectors['y']])
        if 'forms' in columns:
            self.forms = np.array(vectors['forms'])
        if 'rotations' in columns:
            self.rotations = np.array(vectors['rotations'])
        if 'colors' in columns:
            self.colors = np.array(vectors['colors'])
        return self

    @classmethod
    def from_ascii_columns(cls, filename, name='file_geom',
                           columns={'x': 0, 'y': 1}):
        self = cls(name=name, shape=(1,))
        self.read_ascii_columns(filename, columns)
        self.set_shape(self.coords.shape[0])
        return self

    @classmethod
    def from_cp(cls, filename, section='geometry'):
        from ConfigParser import ConfigParser
        cp = ConfigParser()
        cp.read(filename)
        name = cp.get(section, 'name')
        self = cls(name=name, shape=(1,))
        if cp.has_option(section, 'form'):
            self.form = cp.get(section, 'form')
        if cp.has_option(section, 'color'):
            self.form = cp.get(section, 'color')
        # Load the per-pixel data, which is probably in a separate file.
        words = cp.get(section, 'source').split()
        src_type = words.pop(0)
        if src_type == 'ascii':
            geo_file = words.pop(0)
            geo_file = os.path.join(os.path.split(filename)[0], geo_file)
            col_defs = {}
            while len(words) > 1:
                if words[0][0] == '#':
                    break
                field, column = words.pop(0), words.pop(0)
                col_defs[field] = int(column)
            self.read_ascii_columns(geo_file, columns=col_defs)
        # Rescale pixel coordinates?
        if cp.has_option(section, 'rescale'):
            rescale = map(float, cp.get(section, 'rescale').split())
            for i in range(len(rescale)):
                self.coords[i] *= rescale[i]
        # Translate form data?
        if cp.has_option(section, 'form_aliases') and \
                not isinstance(self.forms, basestring):
            translator = dict([x.split() for x in
                               cp.get(section, 'form_aliases').split('\n')
                               if len(x) > 0])
            self.forms = [translator.get(x,x) for x in self.forms]
        # Translate color data?
        if cp.has_option(section, 'color_aliases') and \
                not isinstance(self.colors, basestring):
            translator = dict([x.split() for x in
                               cp.get(section, 'color_aliases').split('\n')
                               if len(x) > 0])
            self.colors = [translator.get(x,x) for x in self.colors]
        # Read the data shape, or set it to a reasonable thing
        if cp.has_option(section, 'shape'):
            self.set_shape(map(int, cp.get(section, 'shape').split()))
        else:
            self.set_shape(len(self.coords[0]))
        # That it all
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
        x -= x.mean()
        y -= y.mean()
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
