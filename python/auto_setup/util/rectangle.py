"""
Class for combining time-ordered data from multiple RCs into a
coherent super-structure.  This is intended for inheritance by the
various ramp and servo objects.  For example, one might acquire SQ2
servo data on several RCs independently, and then either want to work
with the single files or with a synthesized version (without any
difference in the interface).

The data are typically stored in either a 2-d or 3-d array.

The structure information is encoded in attributes

  rows       list of rows
  cols       list of cols
  gridded    boolean specifying that the data are spatially indexed
             with a (row,col) pair, and there are actually 
             (len(rows) x len(cols)) total spatial elements.
             When gridded=False, there is a single spatial dimension and
             len(rows)==len(cols) is the number of spatial elements.

"""

import numpy

class RCData:
    def __init__(self, gridded=False,
                 row_attr='rows', col_attr='cols', data_attrs=['data']):
        self.gridded = gridded
        for a in ['row_attr', 'col_attr', 'data_attrs']:
            setattr(self, a, eval(a))

    def join(self, items):
        """
        items is a list of objects whose data are to be joined.
        """
        if len(items) == 0: return
        # Check integrity
        self.gridded = items[0].gridded
        for i in items[1:]:
            if i.gridded != self.gridded:
                raise RuntimeError, 'items for synthesis differ in structure.'
        if self.gridded:
            # Compute new row and col arrays
            offsets = self._synth_rect_gridded(items)
            # Merge data
            for attr in self.data_attrs:
                self._synth_data_gridded(items, offsets, attr)
        else:
            # Check row/col listings for consistency
            for i in items:
                if len(i.rows) != len(i.cols):
                    raise RuntimeError, 'some items have inconsistent gridding.'
            # Merge row and col arrays
            offsets = self._synth_rect(items)
            # Merge data
            for attr in self.data_attrs:
                self._synth_data(items, offsets, attr)
            

    def _synth_rect(self, items):
        offsets, rows, cols = [], [], []
        for i in items:
            offsets.append(len(rows))
            rows += list(i.rows)
            cols += list(i.cols)
        self.rows, self.cols = rows, cols
        return offsets

    def _synth_rect_gridded(self, items):
        offsets = [(0,0)]
        rows = [i for i in items[0].rows]
        cols = [i for i in items[0].cols]
        for i in items[1:]:
            r, c = list(i.rows), list(i.cols)
            if r == rows:
                offsets.append((0, len(cols)))
                cols += c
            elif c == cols:
                offsets.append((len(rows), 0))
                rows += r
            else:
                raise RuntimeError, 'incompatible row/col structures.'
        self.rows, self.cols = numpy.array(rows), numpy.array(cols)
        return offsets

    def _synth_data(self, items, offsets, attr):
        # Check data shapes (just trust data_shape...)
        d = getattr(items[0], attr)
        dtype, shape_s = d.dtype, tuple(items[0].data_shape[:-3])
        for i in items:
            d = getattr(i, attr)
            if d.dtype != dtype:
                raise RuntimeError, 'data array types differ.'
            if tuple(i.data_shape[:-3]) != shape_s:
                raise RuntimeError, 'secret data structure incompatible'
        # Super data
        nd, nt = len(self.rows), d.shape[-1]
        data = numpy.zeros(shape_s + (nd, nt), dtype=dtype)
        for d, i in zip(offsets, items):
            data[...,d:d+len(i.rows),:] = \
                getattr(i, attr).reshape(shape_s + (len(i.rows), nt))
        setattr(self, attr, data.reshape((-1, nt)))
        self.data_shape = shape_s + (1, nd, nt)

    def _synth_data_gridded(self, items, offsets, attr):
        # Check data shapes (just trust data_shape...)
        d = getattr(items[0], attr)
        dtype, shape_s = d.dtype, tuple(items[0].data_shape[:-3])
        for i in items:
            d = getattr(i, attr)
            if d.dtype != dtype:
                raise RuntimeError, 'data array types differ.'
            if tuple(i.data_shape[:-3]) != shape_s:
                raise RuntimeError, 'secret data structure incompatible'
        # Super data
        nr, nc, nt = len(self.rows), len(self.cols), d.shape[-1]
        data = numpy.zeros(shape_s + (nr, nc, nt), dtype=dtype)
        for (dr, dc), i in zip(offsets, items):
            data[...,dr:dr+len(i.rows),dc:dc+len(i.cols),:] = \
                getattr(i, attr).reshape(shape_s + (len(i.rows),len(i.cols), nt))
        setattr(self, attr, data.reshape((-1, nt)))
        self.data_shape = shape_s + (nr, nc, nt)

