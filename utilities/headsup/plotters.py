import json

import clients
import numpy as np

display_defaults = {
    'autoscale': True,
    'zrange': [-1000,1000],
    }

def mask_to_list(ar):
    return [[int(x) for x in y] for y in ar]

class displayController(dict, clients.dataProducer):
    def __init__(self, addr, name='dispctrl', field=None):
        dict.__init__(self)
        clients.dataProducer.__init__(self, addr, name)
        self.update(display_defaults)

    def post_some(self, keys):
        packet = {}
        for k in keys:
            packet[k] = self[k]
        self.post_meta(packet)
    
    #
    # High level display control
    #

    def autoscale(self, value=None):
        if value == None:
            return self['autoscale']
        self['autoscale'] = value
        self.post_some(['autoscale'])

    def zrange(self, min=None, max=None):
        post = False
        if min != None:
            self['zrange'][0] = min
            post = True
        if max != None:
            self['zrange'][1] = max
            post = True
        if post:
            self.post_some(['zrange'])
        return self['zrange']

    def set_mask(self, mask=None):
        if mask == None:
            return self['mask']
        # json doesn't like numpy's ints.
        self['mask'] = [[int(x) for x in y] for y in mask]
        self.post_some(['mask'])

    def mask_area(self, row=None, col=None, shape=None, unmask=False):
        if 'mask' not in self:
            if shape != None:
                mask = np.zeros(shape, 'bool')
            else:
                print 'Set mask shape first.'
                return False
        else:
            mask = np.asarray(self['mask'], 'bool').transpose()
        if row != None and col != None:
            mask[row, col] = False ^ unmask
        elif row != None:
            mask[row,:] = False ^ unmask
        elif col != None:
            mask[:,col] = False ^ unmask
        else:
            mask[:,:] = False ^ unmask
        self.set_mask(mask_to_list(mask.transpose()))
        
    def unmask_area(self, row=None, col=None, shape=None):
        return self.mask_area(row, col, shape, unmask=True)

    #
    # Save and restore
    #

    def save(self, filename):
        open(filename,'w').write(json.dumps(self))
    
    def restore(self, filename, update=False):
        if not update:
            self.clear()
        d = json.loads(open(filename))
        self.update(d)
        
