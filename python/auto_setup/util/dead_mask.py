from auto_setup.config import mas_param

import numpy
import os

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
        nr = mas_param(filename, 'n_rows', 'integer')
        nc = mas_param(filename, 'n_cols', 'integer')
        d = mas_param(filename, 'mask', 'integer')
        if nr==None or nc==None or d==None:
            raise RuntimeError, 'Invalid or missing dead_mask file "%s"' % filename
        self.data = d.reshape(nc, nr).transpose()
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

    def linear(self, n_rows=None):
        """
        Return a 1-d, integer numpy array of the dead mask, by
        unraveling the column-dominant vector after (possibly)
        trimming or extending it to have n_rows rows.
        """
        if n_rows == None:
            n_rows = self.shape[0]
        nr, nc = self.data.shape[0]
        if nr < n_rows:   # pad the data
            out = zeros((n_rows, nc), dtype=self.data.dtype)
            out[:nr] = self.data
        else:             # view
            out = self.data[:n_rows]
        return out.transpose().ravel().astype('int')

def get_all_dead_masks(tuning, union=False, frail=False):
    """
    Discover and load all dead masks.  Returns list of DeadMask objects.
    """

    if (frail):
        prefix="frail_"
    else:
        prefix="dead_"

    mask_list = tuning.get_exp_param(prefix + "mask_list", missing_ok=True);
    if (mask_list == None):
        mask_list = ["squid1", "multilock", "jumper", "connection", "tes_short",
                "other"]

    mask_files = [ os.environ["MAS_TEMPLATE"] + os.path.join("dead_lists",
            tuning.get_exp_param("array_id"), prefix + m + ".cfg") for m in
            mask_list ]

    mask_files = [m for m in mask_files if os.path.exists(m)]
    masks = [DeadMask(f, label=l) for f,l in zip(mask_files, mask_list)]
    if union:
        if len(masks) == 0:
            return None
        mask = DeadMask(shape=masks[0].shape, label='union')
        mask.data = sum([m.data for m in masks]).astype('bool').astype('int')
        return mask
    return masks

