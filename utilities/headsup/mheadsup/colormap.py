
#
# Round here, colors are always 4-tuples.  R,G,B,alpha.  And for the
# most part each component is a float in [0., 1.].
# 
# "Pivots" refers to a small set of colors, which are used to
# interpolate a full spectrum of colors.  So using pivots of
# [black,white] leads to a gray-scale colormap.
#

COLORMAP_BUILTIN = [
    ('white',     [(0.,0.,0.,1.), (1.,1.,1.,1.)]),
    ('red',       [(0.,0.,0.,1.), (1.,0.,0.,1.)]),
    ('green',     [(0.,0.,0.,1.), (0.,.8,0.,1.)]),
    ('blue',      [(0.,0.,0.,1.), (0.,0.,1.,1.)]),
    ('yellow',    [(0.,0.,0.,1.), (1.,1.,0.,1.)]),
    ('purple',    [(0.,0.,0.,1.), (1.,0.,1.,1.)]),
    ('invisible', [(0.,0.,0.,0.), (0.,0.,0.,0.)]),
    ]

COLORMAP_BUILTIN_DICT = dict(COLORMAP_BUILTIN)


DEFAULT_COLORMAP_PIVOTS = COLORMAP_BUILTIN_DICT['purple']
DEFAULT_COLORMAP_SIZE = 256


class ColorMap:
    size = DEFAULT_COLORMAP_SIZE
    pivots = DEFAULT_COLORMAP_PIVOTS
    colors = None
    scale = None

    def __init__(self, pivots=None, colors=None, size=None, scale=None,
                 name='cmap_custom'):
        self.name = name
        self.scale = scale
        if size != None:
            self.size = size
        if colors == None:
            if pivots != None:
                self.pivots = pivots
            self.make_colors()
        else:
            self.colors = colors

    def make_colors(self, size=None):
        if size != None:
            self.size = size
        if self.size == None:
            self.size = DEFAULT_COLORMAP_SIZE
        speed = float(len(self.pivots)-1)/(self.size-1)
        self.colors = []
        for i in range(self.size-1):
            x = speed*i
            pi = int(x)
            a, b = self.pivots[pi], self.pivots[pi+1]
            self.colors.append(interpolate_colors(a,b,x-pi,self.scale))
        self.colors.append(interpolate_colors(b,b,0.,self.scale))

    def __getitem__(self, index):
        return self.colors[index]

    def __len__(self):
        return self.size

    # Encode / decode from dict (JSON)

    def encode(self):
        if self.colors == None:
            return None
        return {'colors': self.colors}

    @classmethod
    def decode(cls, data):
        if not 'colors' in data:
            return None
        self = cls(colors=data['colors'])


    # Builtins
    @classmethod
    def get_builtin(cls, name, size=None, scale=None):
        if not name in COLORMAP_BUILTIN_DICT:
            raise ValueError, "invalid built-in colormap builtin '%s'"%name
        return cls(pivots=COLORMAP_BUILTIN_DICT[name], size=size,
                   scale=scale)
        

def interpolate_colors(a, b, x, scale=None):
    """
    Return the color (n-tuple) that is x between a and b.  So x would
    normally be in [0,1].  If scale is not None, it should be an
    integer.  In this case the resulting color components are scaled
    by scale, rounded, and truncated.
    """
    if scale == None:
        return [(_b-_a)*x + _a for _a,_b in zip(a,b)]
    return [int(round(scale*(_a + (_b-_a)*x))) for _a,_b in zip(a,b)]
