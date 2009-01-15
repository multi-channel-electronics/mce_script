from mce_data import *
from mce_runfile import *

#filename='/home/mhasse/Desktop/MBAC-May-Coldrun/fast_1211064182'
filename='/data/cryo/current_data/z07'
rf = MCERunfile(filename+'.run')
print rf.Item('HEADER','RB rc2 num_rows', type='int')
print rf.Item2d('HEADER', 'RB bc%i bias', type='int', first=1)
print rf.Item2dRC('HEADER', 'RB rc%i adc_offset%%i', type='int')

filename='/data/cryo/current_data/test_0811'
d = SmallMCEFile(filename=filename, runfile=False)
b = d.Read(fields='all', row_col=True, data_mode=4)
print len(b.data['fb'][0][1])
b = d.Read(data_mode=2)
print len(b.data[2])

dd = d.Read(raw_frames=True)
print dd[:,1]
print dd.shape
