from builtins import map
from builtins import object
import numpy as np

"""
Encoding of arrays as json members.

json has support for arbitrary object reconstruction...
"""

def encode_array_row(data, cast):
    if data.ndim == 1:
        return list(map(cast, data))
    return [encode_array_row(d, cast) for d in data]

def encode_array(data):
    if data is None:
        return None
    dtype = data.dtype.name
    if dtype.startswith('string'):
        cast = str
        dtype = 'string'
    elif dtype.startswith('int'):
        cast = int
    else:
        cast = float
    return {'dtype': dtype,
            'shape': data.shape,
            'data': encode_array_row(data, cast),
            '_class': 'ndarray'}

def decode_array(data):
    if data is None:
        return None
    return np.array(data['data'], dtype=data['dtype'])


class arrayInfoEncoder(object):
    """
    Classlet for serializing simple classes to json-ready dictionaries.

    Special handling is needed for any complex data types.
    """
    arrayInfo_simple = None
    arrayInfo_arrays = None

    def encode(self):
        import json
        output = {}
        if self.arrayInfo_simple is not None:
            for k in self.arrayInfo_simple:
                v = getattr(self, k)
                if isinstance(v, np.ndarray):
                    v = encode_array(v)
                output[k] = v
        # Old array support, remove this soon...
        if self.arrayInfo_arrays is not None:
            out_ar = {}
            for k in self.arrayInfo_arrays:
                d = np.asarray(getattr(self, k))
                out_ar[k] = encode_array(d)
            output['_arrays'] = out_ar
        return output

    @classmethod
    def decode(cls, data):
        self = cls()
        if self.arrayInfo_simple is not None:
            for k in self.arrayInfo_simple:
                v = data.get(k, None)
                if isinstance(v, dict) and '_class' in v:
                    if v['_class'] == 'ndarray':
                        v = decode_array(v)
                setattr(self, k, v)
        # Old array support
        if self.arrayInfo_arrays is not None:
            for k in self.arrayInfo_arrays:
                d = decode_array(data['_arrays'][k])
                setattr(self, k, d)
        return self

