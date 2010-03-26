import distutils.version as dvs
import biggles

# assert biggles.__version__ >= 1.6.4
MIN_BIGGLES = '1.6.4'
if dvs.StrictVersion(MIN_BIGGLES) > biggles.__version__:
    raise RuntimeError, 'This package needs biggles %s or so.' % MIN_BIGGLES


def _carry(idx, lim):
    y = idx[-1] + 1
    if len(lim) == 1 or y < lim[-1]:
        return idx[:-1] + (y,)
    return _carry(idx[:-1], lim[:-1]) + (0,)

def _div_up(x, y):
    """
    int(ceil(x/y))
    """
    return (x + y - 1) / y


class plotGridder:
    """
    Schemer for arranging curves for sets of rows and columns onto
    pages of 4x4 (or so) plots.
    """
    props = [
        ('title', None),
        ('xlabel', None),
        ('ylabel', None),
        ('stacked', True),
        ('rowcol_labels', False),
        ('col_labels', False),
        ('force_vlabel', False),
        ('force_hlabel', False),
        ('target_shape', (4,4)),
        ('img_size', (600, 450)),
        ]

    def __init__(self, shape, filename, **kwargs):
        self.filename = filename
        self.shape = shape

        for k, v in self.props:
            setattr(self, k, v)
        keys = [a for a,_ in self.props]
        for k, v in zip(kwargs.keys(), kwargs.values()):
            if not k in keys:
                raise ValueError, "keyword '%s' not valid" % k
            if v != None:
                setattr(self, k, v)
            
        # Dimensions of target space
        nr, nc = shape
        if nc % 8 != 0:
            raise ValueError, 'give me n_columns = 0 mod 8'
        M, N = self.target_shape[-1::-1]
        S = max(M*N / nc, 1)
        H = _div_up(nc, M*N)
        V = _div_up(nr, S)

        # Store
        self.target_shape = [V, H, S, M, N]

        # Prepare for nextism
        self.reset()

    def __del__(self):
        if not self.written and self.canvas != None:
            self._write_hpage()

    def reset(self):
        self.canvas = None
        self.written = False
        self.plot_files = []
        self.pointer = None

    def _create_hpage_stacked(self):
        V, H, S, M, N = self.target_shape
        v, h, m, n = self.pointer
        page = biggles.Table(1, M)
        for i in range(M):
            page[0,i] = biggles.FramedArray(N,1)
            if self.xlabel != None:
                page[0,i].xlabel = self.xlabel
            if self.ylabel != None:
                page[0,i].ylabel = self.ylabel
            r, c1, _, c2 = self.to_rowcol((v,h,i,0)) + self.to_rowcol((v,h,i,N-1))
            if self.rowcol_labels:
                page[0,i].title = 'Row %2i  Cols %2i-%2i' % (r, c1, c2)
            if self.col_labels:
                page[0,i].title = 'Cols %2i-%2i' % (c1, c2)
        if self.title != None:
            page.title = self.title
        return page
        
    def create_hpage_spotted(self):
        V, H, S, M, N = self.target_shape
        v, h, m, n = self.pointer
        page = biggles.Table(N, M)
        for i in range(M):
            if self.col_labels:
                page[0,i].title = 'Cols %2i-%2i' % (c1, c2)
            for j in range(N):
                page[j,i] = biggles.FramedPlot()
                r, c = self.to_rowcol((v,h,i,j))
                if self.rowcol_labels:
                    page[j,i].title = 'Row %i Col %i' % (r, c)
        if self.title != None:
            page.title = self.title
        return page

    def _create_hpage(self):
        if self.stacked:
            self.canvas = self._create_hpage_stacked()
        else:
            self.canvas = self._create_hpage_spotted()
        self.written = False
    
    def _get_plot(self):
        _,_,m,n = self.pointer
        if self.stacked:
            return self.canvas[0,m][n,0]
        else:
            return self.canvas[n,m]

    def _write_hpage(self):
        V, H,_,_,_ = self.target_shape
        v, h, _, _ = self.pointer
        filename = self.filename
        if V > 1 or self.force_vlabel:
            filename += '_%02i' % v
        if H > 1 or self.force_hlabel:
            filename += '_%i' % ((h+H)%H)
        filename += '.png'
        self.canvas.write_img(self.img_size[0], self.img_size[1], filename)
        self.written = True
        if not filename in self.plot_files:
            self.plot_files.append(filename)

    def index_of(self, row, col):
        V, H, S, M, N = self.target_shape
        vpage = row / S
        hpage = col / (M*N)
        if S == 1:
            major = (col - hpage*(M*N)) / M
            minor = (col - hpage*(M*N)) % M
        else:
            major = (col - (M*N) / S * (row % S)) / M
            minor = (col - (M*N) / S * (row % S)) % M
        return vpage, hpage, major, minor

    def to_rowcol(self, pointer):
        V, H, S, M, N = self.target_shape
        v, h, m, n = pointer
        row = v*S + m*S / M
        if S == 1:
            col = h*M*N + m*N + n
        else:
            col = m*N + n - (m*S / M)*(M*N/S)
        return row, col

    def __iter__(self):
        self.reset()
        return self

    def next(self):
        """
        Returns row, column, and biggles plot object.  Use them wisely.
        """
        # Increment indices
        if self.pointer == None:
            self.pointer = (0,0,0,0)
        else:            
            new_pointer = _carry(self.pointer, self.target_shape[:2] + \
                                     self.target_shape[-2:])
            if new_pointer[-2:] == (0,0) and self.canvas != None:
                self._write_hpage()
            self.pointer = new_pointer

        row, col = self.to_rowcol(self.pointer)
        if row >= self.shape[0]:
            raise StopIteration

        if self.pointer[-2:] == (0,0):
            self._create_hpage()
                
        # Increment
        return row, col, self._get_plot()
