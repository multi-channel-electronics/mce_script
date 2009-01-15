import numpy
from mce_runfile import *

def digits(n, psych=2):
    s = ''
    m = n
    for i in range(32):
        s = '%i%s' % (m & 1, s)
        m = m / 2
    return s

# This maximum is to keep memory usage reasonable.
MAX_FRAMES = 50000

class HeaderFormat:
    """
    Contains description of MCE header content and structure.
    """
    def __init__(self):
        self.offsets = {
            'status': 0,
            'frame_counter': 1,
            'row_len': 2,
            'num_rows_reported': 3,
            'data_rate': 4,
            'address0_ctr': 5,
            'header_version': 6,
            'ramp_value': 7,
            'ramp_addr': 8,
            'num_rows': 9,
            'sync_box_num': 10,
            'runfile_id':  11,
            'userfield': 12,
            }
        self.header_size = 43
        self.footer_size = 1
       
class MCEData:
    """
    Container for MCE data (single channel) and associated header and origin information.
    """
    def __init__(self):
        self.data = {}
        self.source = None
        self.start_frame = 0
        self.n_frames = 0
        self.row = None
        self.col = None
        self.header = None
        self.data_is_dictionary = False
        self.data = []
        self.row_list = []
        self.col_list = []
    
class SmallMCEFile:
    """
    Facilitate the loading of (single channels from) raw MCE
    flat-files.  Extraction and rescaling of data content is performed
    automatically by default.
    """
    def __init__(self, filename=None, do_read = True):
        self.filename = filename
        self.n_frames = 0
        self.n_rows = 0
        self.n_cols = 0
        self.row_list = []
        self.col_list = []
        self.header = None
        self.f = None
        self.runfile = None

    def ReadHeader(self):
        if (self.f == None):
            self.f = open(filename)
            
        # It's a V6.
        format = HeaderFormat()
        head_binary = numpy.fromfile(file=self.f, dtype=numpy.uint32, \
                                         count=format.header_size)

        # Lookup each offset and store
        self.header = {}
        for k in format.offsets:
            self.header[k] = head_binary[format.offsets[k]]
        self.header['rc_present'] = [(self.header['status'] & (1 << 10+i))!=0 \
                                         for i in range(4)]
        self.n_rows = self.header['num_rows_reported']
        self.n_cols = 8*self.header['rc_present'].count(True)
        self.header_size = format.header_size
        self.footer_size = format.footer_size

    def ReadRunfile(self, filename=None):
        if filename == None:
            filename = self.filename + '.run'
        self.runfile = MCERunfile(filename)
        return self.runfile        

    def ReadRaw(self, dets=None, n_frames = MAX_FRAMES, start = 0):
        self.f = open(self.filename)
        if self.header == None:
            self.ReadHeader()
        
        size=self.n_rows*self.n_cols + self.header_size + self.footer_size
        self.f.seek(4*start*size)

        count = size*n_frames
        a = numpy.fromfile(file=self.f, dtype=numpy.uint32, count=count)
        n_frames = len(a) / size
        shape = (n_frames, size)
        a = a.reshape(shape)

        if dets != None:
            det_offsets = [self.header_size + r * self.n_cols + c for (r, c) in dets]
            return numpy.cast['int32'](a[:,det_offsets])

        return numpy.cast['int32'](a[:,self.header_size:self.header_size+self.n_rows*self.n_cols].transpose())

    def NameChannels(self):
        if self.header == None:
            self.ReadHeader()

        rc_p = self.header['rc_present']
        # Columns are entirely determined by what readout cards are present
        rc_cols = [ i for i in range(32) if rc_p[i/8] ]
        self.col_list = rc_cols * self.n_rows

        # We need the runfile to properly designate the readout rows
        if self.runfile == None:
            if self.ReadRunfile() == None:
                print 'Runfile could not be read; using basic channel naming.'
                self.row_list = [ i/self.n_cols for i in range(self.n_cols * self.n_rows)]
                return

        row_index = [ self.runfile.Item('HEADER', 'RB rc%i readout_row_index' %(i+1), type='int', array = False) \
                                       for i in range(4) if rc_p[i] ]
        self.row_list = []
        for r in range(self.n_rows):
            for ri in row_index:
                self.row_list.extend([r + ri] * 8)

    def Read(self, dets = None, n_frames = MAX_FRAMES, start = 0,
             use_runfile = True, do_rescale = True, force_data_mode = None,
             field_list = ['default'], force_dictionary = False):

        self.ReadRunfile()
        data = self.ReadRaw(dets = dets, n_frames = n_frames, start = start)
        self.NameChannels()
        
        data_out = MCEData()
        data_out.source = self.filename
        data_out.n_frames = n_frames
        data_out.header = self.header
        data_out.data_is_dictionary = (len(field_list) > 1 or force_dictionary)
        data_out.row_list = self.row_list
        data_out.col_list = self.col_list

        data_mode = 0
        if force_data_mode != None:
            data_mode = force_data_mode
        else:
            if use_runfile != False:
                if use_runfile == True:
                    runfile_name = self.filename + '.run'
                else:
                    runfile_name = use_runfile
                rf = MCERunfile(runfile_name)
                acq_rc = rf.Item('FRAMEACQ', 'RC', type='int')
                data_mode = rf.Item('HEADER', 'RB rc%i data_mode' % acq_rc[0], type='int', array=False)

        # Define the content and windowing of the 32 bit data.
        data_starts = [0]
        data_counts = [32]
        data_scales = [1.]
        if data_mode == 0:
            data_fields = ['error']
        elif data_mode == 1:
            data_fields = ['fb']
            data_scales = [2**-12]
        elif data_mode == 2:
            data_fields = ['fb_filt']
        elif data_mode == 4:
            data_fields = ['fb', 'error']
            data_starts = [14, 0]
            data_counts = [18, 14]
            data_scales = [1., 1.]
        elif data_mode == 9:
            data_fields = ['fb_filt', 'fj']
            data_starts = [8, 0]
            data_counts = [24, 8]
            data_scales = [2**1, 1.]
        elif data_mode == 10:
            data_fields = ['fb_filt', 'fj']
            data_starts = [7, 0]
            data_counts = [25, 7]
            data_scales = [2**3, 1.]
        else:
            print 'Unimplemented data mode, %i!' % data_mode
            data_fields = ['error']

        if field_list == ['default']:
            field_list = [ data_fields[0] ]

        if field_list == ['all']:
            field_list = data_fields

        if data_out.data_is_dictionary:
            data_out.data = {}

        for f in field_list:
            fidx = data_fields.index(f)

            (c,r) = (5, 37)
#            print data[c,r], digits(data[c,r])
            # shift sign bit into MSB
            left = 32 - data_counts[fidx] - data_starts[fidx]
            right = 32 - data_counts[fidx]
            data_copy = data
            if left != 0:
                data_copy = data_copy * 2**left
#            print data_copy[c,r], digits(data_copy[c,r])
            if right != 0:
                data_copy = data_copy / 2**right
#            print data_copy[c,r], digits(data_copy[c,r])
            if data_scales[fidx] != 1.:
                data_copy = data_copy * data_scales[fidx]
#            print data_copy[c,r]
            if data_out.data_is_dictionary:
                data_out.data[f] = data_copy
            else:
                data_out.data = data_copy
            
        return data_out

