from __future__ import print_function
from builtins import range
import sys
from mce_runfile import *

def check_multilock(filename):
    """
    Check a runfile for 'multilock' detectors that have not been turned off.
    """
    rf = MCERunfile(filename)
    rcs = rf.Item('FRAMEACQ', 'RC', array=True, type='int')
    num_rows = rf.Item('HEADER', 'RB rc%i num_rows' % rcs[0], type='int', array=False)
    multi = rf.Item2d('SQUID','Col%i_squid_multilock',type='int')
    deads = [ rf.Item2d('HEADER', 'RB rc%i gaini' % rc + '%i', type='int') for rc in rcs ]

    broken = 0
    for rci in range(len(rcs)):
        rc = rcs[rci]
        for ch in range(8):
            c = (rc-1)*8 + ch
            for r in range(num_rows):
                if multi[c][r]*deads[rci][ch][r] != 0:
                    print(c,r,multi[c][r],deads[rci][ch][r])
                    broken = broken + 1
    return (broken == 0)

if __name__ == '__main__':
    
    for arg in sys.argv[1:]:
        if check_multi(arg):
            print('Ok   ' +  arg)
        else:
            print('Fail! ' + arg)
