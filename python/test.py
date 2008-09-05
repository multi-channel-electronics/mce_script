import pylab
from mce_data import *
from mce_runfile import *

filename='/home/mhasse/Desktop/MBAC-May-Coldrun/fast_1211064182'
runfile=filename+'.run'
rf = MCERunfile(runfile)
print rf.Item('HEADER','RB rc2 num_rows', type='int')
print rf.Item2d('HEADER', 'RB bc%i bias', type='int', first=1)


d = SmallMCEFile(filename=filename, do_read = False)
b = d.Read(col=0, row=0, force_dictionary = True, field_list = ['all'])
print b.data.keys()
pylab.plot(b.data['error'])
pylab.show()
