from auto_setup.config import mas_param
import numpy

class DeadMask:
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

    def str(self):
        s = 'n_rows = %i;\nn_cols = %i;\n\n' % (self.shape)
        s += 'mask = [\n' \
            '   /* rows:'
        for r in range(self.shape[0]):
            if r%10 == 0: s+= ' '
            s += ' %i' % (r%10)
        s += ' */\n'
        for c in range(self.shape[1]):
            s+=  '   /*c%02i*/  ' % c
            for r in range(self.shape[0]):
                if r%10 == 0: s+= ' '
                s += '%i,' % self.data[r,c]
            s += '\n'
        s = s[:-2] + ' ];\n'
        return s

    def write(self, filename, comment=None):
        f = open(filename, 'w')
        if comment != None:
            if comment[-1] != '\n': comment += '\n'
            f.write(comment)
        f.write(self.str())
        f.close()
        
