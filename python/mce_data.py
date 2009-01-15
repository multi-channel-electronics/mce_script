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

class BitField(object):
    def define(self, name, start, count, scale=1.):
        self.name = name
        self.start = start
        self.count = count
        self.scale = scale
        return self

    def extract(self, data, do_scale=True):
        """
        Extracts the bit field from numpy array of 32-bit integers.
        """
        left = 32 - self.count
        right = left - self.start
        if left != 0:
            data = data * 2**left
        if right != 0:
            data = data / 2**right
        if do_scale and self.scale != 1.:
            data = data * self.scale
        return data

class DataMode(dict):
    def __init__(self):
        dict.__init__(self)
        self.fields = []
    def define(self, *args):
        for a in args:
            self.fields.append(a.name)
            self[a.name] = a
        return self

#Define the MCE data modes
MCE_data_modes = { \
    '0': DataMode().define(BitField().define('error', 0, 32)),
    '1': DataMode().define(BitField().define('fb', 0, 32, 2.**-12)),
    '2': DataMode().define(BitField().define('fb_filt', 0, 32)),
    '4': DataMode().define(BitField().define('fb', 14, 18),
                           BitField().define('error', 0, 14)),
    '9': DataMode().define(BitField().define('fb_filt', 8, 24, 2.**1),
                           BitField().define('fj', 0, 8)),
    '10': DataMode().define(BitField().define('fb_filt', 7, 25, 2.**3),
                            BitField().define('fj', 0, 7)),
}

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
        self.data_is_dict = False
        self.data = []
        self.row_list = []
        self.col_list = []

    
class SmallMCEFile:
    """
    Facilitate the loading of (single channels from) raw MCE
    flat-files.  Extraction and rescaling of data content is performed
    automatically by default.
    """
    def __init__(self, filename=None, runfile=True):
        """
        filename:   path to MCE flatfile
        runfile:    if True (default), filename.run is used.  If False, no runfile is used.
                    Pass a string here to override the runfile filename.
        """
        self.filename = filename
        self.n_frames = 0
        self.n_rows = 0
        self.n_cols = 0
        self.cols_per_card = 0
        self.row_list = []
        self.col_list = []
        self.header = None
        self.f = None
        self.runfile = runfile
        if self.runfile == True:
            self.runfile = filename+'.run'
        self.runfile_data = None

    def ReadHeader(self):
        if (self.f == None):
            self.f = open(filename)
        # It's a V6, or maybe a V7.
        format = HeaderFormat()
        head_binary = numpy.fromfile(file=self.f, dtype=numpy.uint32, \
                                         count=format.header_size)

        # Lookup each offset and store
        self.header = {}
        for k in format.offsets:
            self.header[k] = head_binary[format.offsets[k]]
        self.header['rc_present'] = [(self.header['status'] & (1 << 10+i))!=0 \
                                         for i in range(4)]
        self.header_size = format.header_size
        self.footer_size = format.footer_size
        self.n_rows = self.header['num_rows_reported']
        # On rectangle firmware mode, n_cols is in bits 16:19 of the status word
        if self.header['header_version'] <= 6:
            self.cols_per_card = 8
        else:
            self.cols_per_card = (self.header['status'] >> 16) & 0xf
        self.n_cols = self.cols_per_card*self.header['rc_present'].count(True)

    def ReadRunfile(self):
        """
        Load the runfile data into self.runfile_data, using the filename in self.runfile.
        Returns None if object was initialized without runfile=False
        """
        if self.runfile == False:
            return None
        self.runfile_data = MCERunfile(self.runfile)
        return self.runfile_data

    def ReadRaw(self, dets=None, n_frames=MAX_FRAMES, start=0, raw_frames=False):
        self.f = open(self.filename)
        if self.header == None:
            self.ReadHeader()

        # TRANSITIONAL... check runfile for num_cols!
        print 'TRANSITIONAL, FIX ME'
        rf = self.ReadRunfile()
        if rf != None:
            cols = rf.Item('HEADER', 'RB sys num_cols_reported', type='int')
            if cols != None:
                if cols[0] != self.cols_per_card:
                    print 'Correcting frame size using runfile num_cols_reported...'
                    self.cols_per_card = cols[0]
                    self.n_cols = self.cols_per_card*self.header['rc_present'].count(True)

        size=self.n_rows*self.n_cols + self.header_size + self.footer_size
        self.f.seek(4*start*size)

        count = size*n_frames
        a = numpy.fromfile(file=self.f, dtype=numpy.uint32, count=count)
        self.n_frames = len(a) / size
        shape = (self.n_frames, size)
        a = a.reshape(shape)

        if raw_frames:
            return numpy.cast['int32'](a)
        if dets != None:
            det_offsets = [self.header_size + r * self.n_cols + c for (r, c) in dets]
            return numpy.cast['int32'](a[:,det_offsets]).transpose()
        return numpy.cast['int32'](a[:,self.header_size:self.header_size+self.n_rows*self.n_cols].transpose())

    def NameChannels(self, row_col=False):
        if self.header == None:
            self.ReadHeader()
        rc_p = self.header['rc_present']

        if row_col:
            print 'FIXME: row_list and col_list are still long when row_col==True'

        # We need the runfile to properly designate the readout rows/cols
        if self.runfile_data == None:
            if self.ReadRunfile() == None:
                print 'Runfile could not be read; using basic channel naming.'
                self.row_list = [ i/self.n_cols for i in range(self.n_cols * self.n_rows)]
                self.col_list = [ i%self.n_cols for i in range(self.n_cols * self.n_rows)]
                return

        row_index = [ self.runfile_data.Item('HEADER', 'RB rc%i readout_row_index' %(i+1), type='int', array = False) \
                                       for i in range(4) if rc_p[i] ]
        col_index = [ self.runfile_data.Item('HEADER', 'RB rc%i readout_col_index' %(i+1), type='int', array = False) \
                                       for i in range(4) if rc_p[i] ]
        self.row_list = []
        self.col_list = []
        for r in range(self.n_rows):
            for ri in row_index:
                self.row_list.extend([r + ri] * 8)
        # Not all firmware supports readout_col_index...
        if col_index[0] == None:
            # Columns are entirely determined by what readout cards are present
            rc_cols = [i for i in range(32) if rc_p[i/8]]
        else:
            # Adjust for RC-dependent readout index
            rc_cols = [ 8*rc+col_index[rc]+i for i in range(8) for rc in range(4) if rc_p[rc] ]
        self.col_list = rc_cols * self.n_rows

    def Read(self, dets=None, n_frames=MAX_FRAMES, start=0,
             do_extract=True, do_scale=True, data_mode=None,
             field=None, fields=None, row_col=False,
             raw_frames=False):
        """
        Read MCE data, and optionally extract the MCE signals.

        dets        Pass a list of (row,col) tuples of detectors to extract (None=All)
        n_frames    Number of frames to read
        start       Index of first frame to read
        do_extract  if True, extract signal bit-fields using data_mode from runfile
        do_scale    if True, rescale the extracted bit-fields to match a reference
                    data mode.
        data_mode   Overrides data_mode from runfile, or can provide data_mode if no
                    runfile is used.
        field       A single field to extract.  The output data will contain an array
                    containing the extracted field.  (If None, the default field is used.)
        fields      A list of fields of interest to extract, or 'all' to get all fields.
                    This overrides the value of field, and the output data will contain
                    a dictionary with the extracted field data.
        row_col     if True, detector data is returned as a 3-D array with indices (row,
                    column, frame)
        raw_frames  if True, return a 2d array containing raw data (including header
                    and checksum), with indices (frame, index_in_frame).
        """

        self.ReadRunfile()
        if raw_frames:
            data = self.ReadRaw(n_frames=n_frames, start=start, raw_frames=True)
            return data

        data = self.ReadRaw(dets=dets, n_frames=n_frames, start=start)
        self.NameChannels(row_col=row_col)
        
        data_out = MCEData()
        data_out.source = self.filename
        data_out.n_frames = n_frames
        data_out.header = self.header
        data_out.row_list = self.row_list
        data_out.col_list = self.col_list

        if data_mode == None:
            if self.runfile == False:
                print 'No runfile, forcing data mode 0'
                data_mode = 0
            else:
                if self.runfile_data == None and self.ReadRunfile()==None:
                    print 'Failed to read runfile \'%s\' (suppress with runfile=False)'% \
                        self.runfile
                    return None
                rf = self.runfile_data
                acq_rc = rf.Item('FRAMEACQ', 'RC', type='int')
                data_mode = rf.Item('HEADER', 'RB rc%i data_mode' % \
                                    acq_rc[0], type='int', array=False)

        # NEW CODE
        dm_data = MCE_data_modes.get('%i'%data_mode)
        if dm_data == None:
            print 'Unimplemented data mode %i, treating as 0.'%data_mode
            dm_data = MCE_data_modes['0']

        # This singlular plural thing is a bit lame...
        if field == None:
            field = 'default'

        force_dict = (fields != None)
        if fields == None:
            fields = [field]
        elif fields == 'all':
            fields = dm_data.fields

        for i,f in enumerate(fields):
            if f=='default':
                fields[i] = dm_data.fields[0]                

        data_out.data_is_dict = (len(fields) > 1 or force_dict)
        if data_out.data_is_dict:
            data_out.data = {}

        for f in fields:
            # Use BitField.extract to get each field
            new_data = dm_data[f].extract(data, do_scale=do_scale)
            if row_col:
                new_data.shape = (self.n_rows, self.n_cols, self.n_frames)
            if data_out.data_is_dict:
                data_out.data[f] = new_data
            else:
                data_out.data = new_data

        return data_out

