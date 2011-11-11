"""
Searches for duplicate data in MCE files.

In particular, scan up to 10000 readout frames of an MCE file and
identify indices in frame n-1 that are always duplicated at some fixed
index in frame n.

For example, the last 6 samples in a readout frame might always be
repeated as the first 6 samples of the next frame.  This would be reported as:

    Filename: noise300_r20c12_b600_noise
     readout size:      256
     duplicate runs:      1
          length   prev_frame  frame
              6        -6         0
"""

from pylab import *
from mce_data import *

def pick(raw, ofs1, ofs2, count):
    n = raw.shape[-1]
    if ofs1 < 0: ofs1 = ofs1+n
    if ofs2 < 0: ofs2 = ofs2+n
    dz = raw[1:,ofs2:ofs2+count] - raw[:-1,ofs1:ofs1+count]
    return dz

def hunt(raw):
    # Get candidates by looking for duplicated entries in first and
    # second frames.
    n = raw.shape[1]
    cand = []
    for ofs in range(1, n):
        count = n - ofs
        d = pick(raw[:2],ofs,0,count) # raw[0,ofs:] - raw[1,:count]
        for i in (d[0]==0).nonzero()[0]:
            cand.append((ofs+i, i))
    #print 'Initial cands: ', len(cand)
    # Test cands globally
    ok = []
    for a, b in cand:
        if all(pick(raw, a, b, 1)==0):
            ok.append((a,b))
    #print 'Verified: ', len(ok)
    # Reduce to runs
    cand = []
    running = None
    for a, b in sorted(ok):
        if running == (a-1, b-1):
            # Just increment count
            cand[-1][2] += 1
        else:
            # New beginning
            cand.append([a,b,1])
        running = a, b
    return cand

from optparse import OptionParser
o = OptionParser()
opts, args = o.parse_args()

for filename in args:
    # Load file
    print 'Filename: %s' % filename
    m = MCEFile(filename, runfile=False)
    # Load raw frames, 10 k should be enough.
    rawd = m.Read(raw_frames=1)[:10000]
    # Discard header / checksum.
    raw = rawd[:,43:-1]
    # Look for duplicates
    runs = hunt(raw)
    n = raw.shape[-1]
    print ' readout size:    %5i' % n
    print ' duplicate runs:  %5i' % len(runs) 
    if len(runs)>0:
        print     '      length   prev_frame  frame'
        for a,b,c, in runs:
            print '        %3i       %3i       %3i' % (c, a-n,b)
