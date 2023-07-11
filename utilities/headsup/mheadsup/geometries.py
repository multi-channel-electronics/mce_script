from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import range
import os
import numpy as np

"""
Classes describing layouts and shape of picture elements.

Also tracking of multiple layouts, encoding, decoding...
"""

from .encoders import arrayInfoEncoder as aie

class pixelSetGeometry(aie):
    """
    Record positions of a set of pixels.
    """
    arrayInfo_simple= ['name', 'n_pix', 'n_dim', 'data_shape', 'props',
                       'coords', 'forms', 'rotations', 'colors', 'mask',
                       'channel_names']

    def __init__(self, name='geom', shape=None):
        if shape is None:
            shape = (0,)
        self.set_shape(shape)
        self.coords = np.zeros(self.data_shape)
        self.forms = 'square'
        self.colors = 'purple'
        self.rotations = 0.
        self.name = name
        self.props = {}
        self.mask = True
        self.channel_names = None

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
        if dims is None:
            dims = [i for i in range(self.n_dim)]
        if idx is None:
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
                           columns={'x': 0, 'y': 1},
                           translators={}):
        casts = {'x': float,
                 'y': float,
                 'forms': str,
                 'rotations': float,
                 'colors': str,
                 'mask': int,
                 'names': str,
                 }
        data = []
        for k in list(casts.keys()):
            if k in columns:
                data.append((k, columns[k],
                             casts[k], translators.get(k,{}),
                             []))
        
        for line in open(filename):
            w = line.split()
            if len(w) == 0 or w[0][0] == '#':
                continue
            for k, col, cst, trans, d in data:
                d.append(cst(trans.get(w[col], w[col])))
        vectors = {}
        for k, _,_,_, d in data:
             vectors[k] = np.array(d)
        self.coords = np.array([vectors['x'], vectors['y']])
        if 'forms' in columns:
            self.forms = np.array(vectors['forms'])
        if 'rotations' in columns:
            self.rotations = np.array(vectors['rotations'])
        if 'colors' in columns:
            self.colors = np.array(vectors['colors'])
        if 'mask' in columns:
            self.mask = np.array(vectors['mask']).astype('bool')
        if 'names' in columns:
            self.channel_names = np.array(vectors['names'])
        return self

    @classmethod
    def from_ascii_columns(cls, filename, name='file_geom',
                           columns={'x': 0, 'y': 1}):
        self = cls(name=name, shape=(1,))
        self.read_ascii_columns(filename, columns)
        self.set_shape(self.coords.shape[0])
        return self

    @staticmethod
    def get_cp_list(filename):
        from configparser import ConfigParser
        cp = ConfigParser()
        cp.read(filename)
        return cp.sections()

    @classmethod
    def from_cp(cls, filename, section='geometry'):
        from configparser import ConfigParser
        cp = ConfigParser()
        cp.read(filename)
        name = cp.get(section, 'name')
        self = cls(name=name, shape=(1,))
        if cp.has_option(section, 'form'):
            self.form = cp.get(section, 'form')
        if cp.has_option(section, 'color'):
            self.form = cp.get(section, 'color')
        # Load column translation information before file load
        def get_trans_table(lines):
            return dict([x.split() for x in lines.split('\n')
                         if len(x) > 0])
        translators = {}
        ## Aliases for form names
        if cp.has_option(section, 'form_aliases'):
            translators['forms'] = get_trans_table(
                cp.get(section, 'form_aliases'))
        ## Color aliases
        if cp.has_option(section, 'color_aliases'):
            translators['colors'] = get_trans_table(
                cp.get(section, 'color_aliases'))
        ## Mask aliases
        if cp.has_option(section, 'mask_aliases'):
            translators['mask'] = get_trans_table(
                cp.get(section, 'mask_aliases'))

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
            self.read_ascii_columns(geo_file, columns=col_defs,
                                    translators=translators)

        # Rescale pixel coordinates?
        if cp.has_option(section, 'rescale'):
            rescale = list(map(float, cp.get(section, 'rescale').split()))
            for i in range(len(rescale)):
                self.coords[i] *= rescale[i]

        # Read the data shape, or set it to a reasonable thing
        if cp.has_option(section, 'shape'):
            self.set_shape(list(map(int, cp.get(section, 'shape').split())))
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
        if x is None:
            x = np.arange(n_col)
        if y is None:
            y = np.arange(n_row)
        x = np.asarray(x).reshape((1,-1)).astype('float')
        y = np.asarray(y).reshape((-1,1)).astype('float')
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
        if radius is None:
            radius = 1.2 * n_pix / 2 / np.pi
        theta = 2 * np.pi * np.arange(n_pix) / n_pix
        self.coords = np.array([radius*np.cos(theta), radius*np.sin(theta)])
        self.name = name
        return self
