#!/usr/bin/python

from mce import *
from numpy import *
import interservo


class SmartMCE(mce):
    def __init__(self):
        mce.__init__(self)
        self.n_rc = 2
        self.n_ch = 8
        self.n_col = self.n_rc * self.n_ch
        self.n_row = 41

    def readArrayRC(self, param):
        """
        Read a parameter that is stored in per-column registers on
        multiple readout cards into a single n_row x n_col array.

        Param should contain a %i argument -- it will be filled with
        the channel index.
        """
        data = zeros((self.n_row, self.n_col), dtype='int')
        if param == 'fb_col%i':
            for c in range(self.n_col):
                x = self.read('sq2', param % c, count=self.n_row)
                data[:len(x),c] = x
        else:
            for r in range(self.n_rc):
                for ch in range(self.n_ch):
                    x = self.read('rc%i' % (r+1), param % ch)
                    data[:len(x),r*8+ch] = x
        return data

    def writeArrayRC(self, param, data):
        nr, nc = data.shape
        for c in range(nc):
            x = self.write('rc%i' % (c/8+1), param % (c%8), data[:,c])
        

if __name__ == '__main__':
    m = SmartMCE()
    n_row = 33
    servo_i = m.readArrayRC('gaini%i')[:n_row,:]
    adc_offset = m.readArrayRC('adc_offset%i')[:n_row,:]
    change_mask = zeros(adc_offset.shape, dtype='bool')

    for c in range(m.n_col):
        a = hstack((adc_offset[:,c], adc_offset[:,c])).ravel()
        s = hstack((servo_i[:,c], servo_i[:,c])).ravel()
        targets = s.nonzero()[0]
        for r1, r2 in zip(targets[:-1], targets[1:]):
            if (r2 - r1) <= 1: continue
            print c, r1, r2, 'uh',
            # Fill intervening rows
            p = polyfit([r1, r2], a[[r1,r2]], 1)
            print a[r1:r2+1], ' --> ',
            a[r1+1:r2] = polyval(p, arange(r1+1, r2), )
            print a[r1:r2+1]
            idx = arange(r1+1, r2) % n_row
            adc_offset[idx,c] = a[idx]
            change_mask[idx,c] = True
        
    # Write these new adc_offset targets
    m.writeArrayRC('adc_offset%i', adc_offset)

    # Reservo the SQ2 on these channels
    fb_before = m.readArrayRC('fb_col%i')
    gains = array(interservo.expt_param('sq2servo_gain', dtype='float'))
    gains = (gains[:m.n_rc].reshape(1,-1) + zeros((m.n_ch, 1))).ravel()
    interservo.reservo_all(m, gains=gains, n_rows=n_row, n_cols=m.n_col, steps=20)
    fb_after = m.readArrayRC('fb_col%i')
    print fb_after[change_mask] - fb_before[change_mask]
    
