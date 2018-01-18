import os, shutil
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


class pageIndexer:
    """
    Spread a grid of a certain size over several pages of a smaller size,
    preserving row and column structure.
    """
    def __init__(self, page_shape, world_shape):
        self.page_shape = page_shape
        self.world_shape = world_shape
        self.world_pages = [_div_up(world_shape[0], page_shape[0]),
                            _div_up(world_shape[1], page_shape[1])]
        # slowwww
        self.indices = sorted([(self.index(r, c),(r,c)) \
                                   for r in range(world_shape[0]) \
                                   for c in range(world_shape[1])])

    def index(self, r, c):
        # return page number and page row, col
        dr, dc = self.page_shape
        nr, nc = self.world_shape
        page_r, page_c = (r/dr), (c/dc)
        page = page_r * self.world_pages[1] + page_c
        return (page, r%dr, c%dc)

    def __iter__(self):
        self.index = 0
        return self

    def next(self):
        if self.index >= len(self.indices):
            raise StopIteration
        self.index += 1
        return self.indices[self.index-1]


class plotPager:
    """
    Generic organizer for grouping objects (e.g. plots) onto pages
    in a systematic way.
    """
    props = [
        ('shape', (4,4)),
        ('page_shape', (4,4)),
        ]

    def __init__(self, **kwargs):
        """
        page_shape
        shape
        """
        for k, v in self.props:
            v = kwargs.get(k, v)
            setattr(self, k, v)
        self.pi = pageIndexer(self.page_shape, self.shape)
        self.reset()

    def __del__(self):
        self.write_page()

    def reset(self):
        self.canvas = None
        self.last_page = None
        self.iter = None

    # Iterator returns world row, column and a plot object
    def __iter__(self):
        self.iter = self.pi.__iter__()
        self.last_page = None
        self.canvas = None
        return self

    def next(self):
        (p, pr, pc), (r, c) = self.iter.next()
        if p != self.last_page and self.canvas is not None:
            self.write_page()
        self.last_page = p
        return r, c, self.get_container(p, pr, pc)

    # Methods for inheritance
    def write_page(self):
        pass

    def get_page(self, page):
        pass

    def get_container(self, page, prow, pcol):
        pass

class bigglesPager(plotPager):
    props = [
        ('img_size', (600, 450)),
        ('filename', None),
        ]
    def __init__(self, *args, **kwargs):
        self.props = plotPager.props + self.props
        plotPager.__init__(self, *args, **kwargs)
    def get_page(self, page):
        pr, pc = self.page_shape
        filename = self.filename % page
        plot = biggles.Table(pr, pc)
        for i in range(pc):
            for j in range(pr):
                plot[j,i] = biggles.FramedPlot()
        self.canvas = {
            'filename': filename,
            'plot': plot,
            }
    
    def get_container(self, page, prow, pcol):
        if self.canvas is None:
            self.get_page(page)
        return self.canvas['plot'][prow,pcol]

    def write_page(self):
        c = self.canvas
        if c is None:
            return None
        pr, pc = self.page_shape
        for i in range(pr):
            for j in range(pc):
                p = c['plot'][i,j]
                if p.empty():
                    p.add(biggles.Curve([0],[0]))
        c['plot'].write_img(self.img_size[0], self.img_size[1],
                            c['filename'])
        self.canvas = None
        return c['filename']


class stackedPager(bigglesPager):
    def get_page(self, page):
        pr, pc = self.page_shape
        filename = self.filename % page
        plot = biggles.Table(1, pc)
        for i in range(pc):
            plot[0,i] = biggles.FramedArray(pr,1)
        self.canvas = {
            'filename': filename,
            'plot': plot,
            }
    
    def get_container(self, page, prow, pcol):
        if self.canvas is None:
            self.get_page(page)
        return self.canvas['plot'][0,pcol][prow,0]

    def write_page(self):
        c = self.canvas
        if c is None:
            return None
        pr, pc = self.page_shape
        c['plot'].write_img(self.img_size[0], self.img_size[1],
                            c['filename'])
        self.canvas = None
        return c['filename']


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
        ('row_labels', False),
        ('force_vlabel', False),
        ('force_hlabel', False),
        ('target_shape', (4,4)),
        ('img_size', (600, 450)),
        ('format', 'png'),
        ]

    def __init__(self, shape, filename, **kwargs):
        self.filename = filename

        for k, v in self.props:
            setattr(self, k, v)
        keys = [a for a,_ in self.props]
        for k, v in zip(kwargs.keys(), kwargs.values()):
            if not k in keys:
                raise ValueError, "keyword '%s' not valid" % k
            if v is not None:
                setattr(self, k, v)
            
        # Dimensions of target space
        nr, nc = shape
        if nc % 8 != 0:
            nc = (nc+7) / 8 * 8
        self.shape = (nr, nc)

        M, N = self.target_shape[-1::-1]
        S = max(M*N/nc, 1)
        H = _div_up(nc, M*N)
        V = _div_up(nr, S)

        # Store
        self.target_shape = [V, H, S, M, N]

        # Prepare for nextism
        self.reset()

    def cleanup(self):
        if not self.written and self.canvas is not None:
            self._write_hpage()
        ofile = self.filename + '.pdf'
        if self.format == 'pdf' and not os.path.exists(ofile):
            pp = pdfCollator(self.plot_files, ofile)
            if pp.collate(remove_sources=True):
                self.plot_files = [ofile]

    def __del__(self):
        self.cleanup()

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
            if self.xlabel is not None:
                page[0,i].xlabel = self.xlabel
            if self.ylabel is not None:
                page[0,i].ylabel = self.ylabel
            r, c1, _, c2 = self.to_rowcol((v,h,i,0)) + self.to_rowcol((v,h,i,N-1))
            if self.rowcol_labels:
                page[0,i].title = 'Row %2i  Cols %2i-%2i' % (r, c1, c2)
            if self.col_labels:
                page[0,i].title = 'Cols %2i-%2i' % (c1, c2)
            if self.row_labels:
                page[0,i].title = 'Rows %2i-%2i' % (c1, c2) # :P
        if self.title is not None:
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
        if self.title is not None:
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
        if self.format == 'png':
            filename += '.png'
        else:
            filename += '.svg'
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
        if self.pointer is None:
            self.pointer = (0,0,0,0)
        else:            
            new_pointer = _carry(self.pointer, self.target_shape[:2] + \
                                     self.target_shape[-2:])
            if new_pointer[-2:] == (0,0) and self.canvas is not None:
                self._write_hpage()
            self.pointer = new_pointer

        row, col = self.to_rowcol(self.pointer)
        if row >= self.shape[0]:
            raise StopIteration

        if self.pointer[-2:] == (0,0):
            self._create_hpage()
                
        # Increment
        return row, col, self._get_plot()


def hack_svg_viewbox(src, dest):
    """
    Convert a biggles/libplot-generated SVG file (src) to one suitable
    for consumption by svg2rlg and save in dest.

    Rescales the SVG viewBox from (0,1) to (0,npix).  The PDF
    converter seems to insist on interpreting the viewBox coordinates
    as the desired image width in pixels.
    """
    import re
    from xml.dom import minidom

    md = minidom.parse(src)
    svg = md.childNodes[1]
    # Find our tags of interest
    for x in svg.childNodes:
        if x.nodeName == 'rect' and x.getAttribute('id') =='background':
            bg_rect = x
        elif x.nodeName == 'g':
            svg_g = x
    # Get transform atoms
    transforms = svg_g.getAttribute('transform')
    t_atoms = re.findall('([a-z]*\([^\)]*\))', transforms)
    # Get the keyword and first two arguments for each transform
    t_data = [ re.match('([a-zA-z]*)\(([0-9.\-]*)[\ ,]([0-9.\-]*).*\)', t)
               for t in t_atoms]
    t_data = [ (t.group(1), t.group(2), t.group(3)) for t in t_data]
    # The "scale" secretly holds the original libplot image size.
    for n, x, y in t_data:
        if n == 'scale':
            x, y = float(x), float(y)
            break
    else:
        raise RuntimeError, "Could not find scale argument"
    xsize, ysize = int(round(1/x)), int(round(-1/y))
    # New coordinate description
    svg_g.setAttribute('transform', 'translate(0 %i) scale(1 -1)' % ysize)
    svg.setAttribute('viewBox', '0 0 %i %i' % (xsize, ysize))
    bg_rect.setAttribute('width', str(xsize))
    bg_rect.setAttribute('height', str(ysize))
    fout = open(dest, 'w')
    md.writexml(fout)
    del fout


class pdfCollator:
    """
    Combine some SVGs into a single PDF.
    """
    def __init__(self, sources, dest):
        self.sources = sources
        self.dest = dest

    def collate(self, remove_temp=True, remove_sources=False):
        from pyPdf import PdfFileWriter, PdfFileReader
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
            
        # Make temporary folder
        dest_dir, _ = os.path.split(self.dest)
        if not os.path.exists(dest_dir):
            raise RuntimeError, "output place %s d.n.e."% dest_dir
        temp_dir = dest_dir + '/tmp'
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)
        # Fix SVG windows for PDFing
        temp_page = ['%s/page%i.tmp' % (temp_dir, i)
                     for i,_ in enumerate(self.sources)]
        for s, d in zip(self.sources,temp_page):
            hack_svg_viewbox(s, d)
        # Generate single PDF pages
        for s in temp_page:
            drawing = svg2rlg(s)
            renderPDF.drawToFile(drawing, s, autoSize=1)
        # Concatenate the PDF pages into a single document
        output = PdfFileWriter()
        for s in temp_page:
            i = PdfFileReader(open(s,'rb'))
            output.addPage(i.getPage(0))
            del i
        fout = file(self.dest, 'wb')
        output.write(fout)
        fout.close()
        # Remove the temporary folder
        if remove_temp:
            shutil.rmtree(temp_dir)
        # Remove the source images
        if remove_sources:
            map(os.remove, self.sources)
        return True
