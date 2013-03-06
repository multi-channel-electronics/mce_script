import numpy as np

"""
Encoding of arrays as json members.

json has support for arbitrary object reconstruction...
"""

def encode_array_row(data):
    if data.ndim == 1:
        return map(float, data)
    return [encode_array_row(d) for d in data]

def encode_array(data):
    if data == None:
        return None
    return {'dtype': data.dtype.name,
            'data': encode_array_row(data)}

def decode_array(data):
    if data == None:
        return None
    return np.array(data['data'], dtype=data['dtype'])


class arrayInfoEncoder:
    """
    Classlet for serializing simple classes to json-ready dictionaries.

    Special handling is needed for any complex data types.
    """
    arrayInfo_simple = None
    arrayInfo_arrays = None

    def encode(self):
        import json
        output = {}
        if self.arrayInfo_simple != None:
            for k in self.arrayInfo_simple:
                output[k] = getattr(self, k)
        if self.arrayInfo_arrays != None:
            out_ar = {}
            for k in self.arrayInfo_arrays:
                d = np.asarray(getattr(self, k))
                out_ar[k] = encode_array(d)
            output['_arrays'] = out_ar
        return output

    @classmethod
    def decode(cls, data):
        self = cls()
        if self.arrayInfo_simple != None:
            for k in self.arrayInfo_simple:
                setattr(self, k, data[k])
        if self.arrayInfo_arrays != None:
            for k in self.arrayInfo_arrays:
                d = decode_array(data['_arrays'][k])
                setattr(self, k, d)
        return self

