import numpy as np

"""
Masks.  An enum the same shape as the data.
"""

from encoders import arrayInfoEncoder as aie

class pixelMask(aie):
    """
    An integer enum for each pixel.
    """
    arrayInfo_simple= ['name', 'states']
    arrayInfo_arrays = ['data']

    def __init__(self, name='mask', shape=None, states=None, data=None):
        self.name = name
        if data != None:
            self.data = data
            self.shape = shape
        else:
            if shape == None:
                shape = (0,)
            self.data = np.zeros(shape, 'int')

    def get_mask(self, state):
        if not isinstance(state, int):
            if state in self.states:
                state = self.states.index(state)
            else:
                print 'unknown state "%s"' % state
                return np.zeros(self.data.shape, 'bool')
        return self.data == state

    @classmethod
    def load_ascii(cls, filename):
        shape = None
        data = None
        name = ''
        states = []
        line_num = 0
        for line in open(filename):
            line_num += 1
            w = line.split()
            if len(w) == 0 or w[0][0] == '#':
                continue
            # First token is the command
            cmd = w.pop(0)
            if cmd == 'shape':
                shape = tuple([int(x) for x in w])
                ndim = len(shape)
                data = np.zeros(shape, 'int')
            elif cmd == 'name':
                name = w.pop(0)
            elif cmd == 'state':
                while len(w) > 0:
                    if w[0] == '#':
                        break
                    states.append(w.pop(0))
            elif cmd == 'set':
                coords = tuple([int(w.pop(0)) for i in range(ndim)])
                data[coords] = int(w.pop(0))
            elif cmd == 'all':
                data[:] = int(w.pop(0))
            elif cmd == 'row' or cmd == 'y':
                i, val = [int(w.pop(0)) for i in range(2)]
                data[i] = val
            elif cmd == 'col' or cmd == 'x':
                i, val = [int(w.pop(0)) for i in range(2)]
                data[:,i] = val
            else:
                print 'unknown command %s on line %i of %s' % \
                    (cmd,line_num,filename)
                continue
            if len(w) > 0 and w[0][0] != '#':
                print 'stray stuff on line %i of %s' % \
                    (line_num,filename)
        # Enough states?
        i_max = data.max()
        while len(states) <= i_max:
            states.append('state_%i'% (len(states)-1))
            
        self = cls(shape=shape, name=name, states=states)
        self.data = data
        return self
                
