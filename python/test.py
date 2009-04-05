import mce_data
from mce_data import *
import sys

if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    filename = '/home/data/act/2008/AR3/0906/1220748172/1220748209_RC3_ssa'

rf = MCERunfile(filename+'.run')
print rf.Item('HEADER','RB rc2 num_rows', type='int')
print rf.Item2d('HEADER', 'RB bc%i bias', type='int', first=1)
print rf.Item2dRC('HEADER', 'RB rc%i adc_offset%%i', type='int')

d = MCEFile(filename=filename, runfile=True)
print 'Reading %s' %filename
b = d.Read(fields='all', row_col=True, data_mode=4)
print len(b.data['fb'][0][1])
print 'Reading %s' %filename
b = d.Read(data_mode=2)
print len(b.data[2])

print 'Reading %s' %filename
dd = d.Read(raw_frames=True)
print dd[:,1]
print dd.shape
print 'Reading %s' %filename

mce_data.MAX_READ_SIZE = 10000
dd = d.Read(count = 10, start = 2)
