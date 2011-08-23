"""
Sometimes you might want to dump a runfile into config options,
or mas_param calls, or something.
"""

import sys
from mce_data import MCERunfile

from optparse import OptionParser
o = OptionParser()
o.add_option('-m','--mas-param',action='store_true')
opts, args = o.parse_args()


src = args[0]
if len(args) > 1:
    fout = open(args[1])
else:
    fout = sys.stdout

fin = MCERunfile(src)

pairs = [
    ('default_sa_bias', 'RB sa bias'),
    ('default_sq2_bias', 'RB sq2 bias'),
    ('default_sq1_bias', 'RB ac on_bias'),
    ('default_sq1_bias_off', 'RB ac off_bias'),
]

for k1, k2 in pairs:
    d = fin.Item('HEADER', k2, type='int', array=True)
    if opts.mas_param:
        fout.write('mas_param set %s '%k1)
        fout.write(' '.join(['%i'%x for x in d]) + '\n')
    else:
        fout.write('%s = [\n' % k1)
        nr = (len(d)+7)/8
        for i in range(nr):
            fout.write(' ' * 10 + ', '.join(['%6i'%x for x in d[i*8:i*8+8]]))
            if i != nr-1:
                fout.write(',\n')
            else:
                fout.write('];\n')

