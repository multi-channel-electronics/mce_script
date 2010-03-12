from auto_setup.config import mas_param
import numpy

class dead_mask:
    def __init__(self, filename=None, label='', shape=None):
        """
        Provide filename to load dead mask, or pass dimensions in 'shape' to
        create empty mask.  Label may be consumed by plotters, etc.
        """
        if filename != None:
            self.read(filename)
        elif shape != None:
            self.shape = shape
            self.data = numpy.zeros(shape, dtype='int')
        self.label = label

    def read(self, filename):
        nr = mas_param(filename, 'n_rows', 0)
        nc = mas_param(filename, 'n_cols', 0)
        self.data = mas_param(filename, 'mask', 0).reshape(nc, nr).transpose()
        self.shape = self.data.shape
