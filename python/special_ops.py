from __future__ import division
from __future__ import print_function
from builtins import chr
from builtins import range
from builtins import object
from past.utils import old_div
usage="""
%prog [options] action [action, ...]

Recognized actions:

 measure_sa_offset_ratio

   Measure the ADC response to changes in SA bias and SA offset and
   estimate an appropriate value to use for sa_offset_bias_ratio.

 test_syncbox

   Check for connection to syncbox.  This only tests for presence of
   the Manchester clock; it can't see whether configuration is correct.
"""

from mce_control import mce_control as mce

# Kinds of readout card

class RC_revE(object):
    # Overall gain of SA output to ADC input
    output_gain = 202.36
    # SA output voltage per ADC bit
    dVdX_adc = 2.00/2**14 / 202.36
    # SA output voltage per bit of offset DAC
    dVdX_offset = 2.5/2**16 / 45.92
    # SA bias voltage, per bit of bias DAC
    dVdX_bias = old_div(2.5,2**16)
    # SA bias resistance (not including cable)
    R_bias = 15000.

class RC_revB(object):
    # Overall gain of SA output to ADC input
    output_gain = 198.9
    # SA output voltage per ADC bit
    dVdX_adc = 2.20/2**14 / 198.9
    # SA output voltage per bit of offset DAC
    dVdX_offset = 2.5/2**16 / 33.90
    # SA bias voltage, per bit of bias DAC
    dVdX_bias = old_div(2.5,2**16)
    # SA bias resistance (not including cable)
    R_bias = 15000.

RC_revs = {
    2: RC_revB,
    5: RC_revE,
}


from  optparse import OptionParser

o = OptionParser(usage=usage)
opts, args = o.parse_args()


for action in args:
    if action == 'measure_sa_offset_ratio':
        m = mce()
        print('Saving current configuration...')
        sa_bias0 = m.read('sa', 'bias')
        sa_offset0 = m.read('sa', 'offset')
        sample_num = m.read('rca', 'sample_num')[0]
        card_rev = m.read('rca', 'card_type')[0] >> 16
        if card_rev == 0:
            card_rev = 2
        servo0, data0 = m.servo_mode(), m.data_mode()
        
        print('Setting up...')
        n_sa = len(sa_bias0)
        m.servo_mode(0)
        m.data_mode(0)

        print('Measuring SA bias response...')
        step = 500
        m.write('sa', 'bias', [0]*n_sa)
        m.write('sa', 'offset', [0]*n_sa)
        y0 = m.read_row()
        
        m.write('sa', 'bias', [step]*n_sa)
        y1 = m.read_row()
        
        m.write('sa', 'offset', [step]*n_sa)
        y2 = m.read_row()

        m.write('sa', 'bias', [0]*n_sa)
        y3 = m.read_row()

        print('Restoring...')
        m.write('sa', 'offset', sa_offset0)
        m.write('sa', 'bias', sa_bias0) 
        m.servo_mode(servo0)
        m.data_mode(data0)
        
        # Measure response to SA bias:
        d_bias   = (y1 - y0).astype('float') / step / sample_num
        #d_offset = y1 - y2
        ## This is better because it catches open circuits
        d_offset = (y0 - y3).astype('float') / step / sample_num
        ratio = old_div(d_bias.astype('float'), d_offset)
        if any(d_offset==0):
            ratio[d_offset==0] = 0
        
        print('SA response (dADC/dBIAS), by column:')
        for r in range(old_div((n_sa+7),8)):
            print('  ', ' '.join(['%7.3f' % x
                                  for x in d_bias[r*8:(r+1)*8]]))
        print()

        print('Offset response (dDC/dOFFSET), by column:')
        for r in range(old_div((n_sa+7),8)):
            print('  ', ' '.join(['%7.3f' % x
                                  for x in d_offset[r*8:(r+1)*8]]))
        print()

        # Analyze those signals
        rc = RC_revs[card_rev]
        d_offset_pred = old_div(rc.dVdX_offset, rc.dVdX_adc)

        # Convert d_bias to voltage ratio between SA output (at
        # pre-amp input) and SA bias (at DAC output)
        dVdV_bias = (d_bias * rc.dVdX_adc / rc.dVdX_bias)**-1
        ## Using R_bias, determine R_cable.
        R_cable = old_div(rc.R_bias, (dVdV_bias - 1))

        ## Flags
        offset_good = abs(old_div(d_offset,d_offset_pred) - 1) < .01

        print('Estimated SA cable resistance (rev%s readout card):' % \
            chr(ord('A')-1+card_rev))
        for r in range(old_div((n_sa+7),8)):
            print('  ', ' '.join(['%7.1f' % x for x in R_cable[r*8:(r+1)*8]]))
        print()


        print('Apparent resistance ratios, by column:')
        for r in range(old_div((n_sa+7),8)):
            print('  ', ' '.join(['%7.3f' % x for x in ratio[r*8:(r+1)*8]]))
        ratio_mean = ratio[ratio!=0].mean()
        print()
        print('The typical ratio is:  %.3f' % ratio_mean)
        print()

        # This ratio isn't necessarily what you want to use, you might
        # want to let the floor drop out gradually
        sa_max = old_div(64000., step)
        sa_fall = -8000*sample_num - y0
        ratio1 = old_div(-(old_div(sa_fall, sa_max) - d_bias), d_offset)
        ratio1[d_offset==0] = 0.
        print('Suggested sa_offset_bias_ratios, by column:')
        for r in range(old_div((n_sa+7),8)):
            print('  ', ' '.join(['%7.3f' % x for x in ratio1[r*8:(r+1)*8]]))
        ratio1_min = ratio1[ratio1!=0].min()
        print('Smallest range-filling ratio: %.3f' % ratio1_min) 

        # Rough badness diagnostic
        if ratio1_min < ratio_mean:
            print('You have weird ratios.  Seek advice.')
        print('Recommended sa_offset_bias_ratio: %.3f' % ratio1_min)

    elif action == 'test_syncbox':
        m = mce()
        for it in [0,1]:
            sc0 = m.read('cc', 'select_clk')
            if sc0 is None:
                print('MCE error.')
                break
            elif sc0[0] == 1:
                print('Sync box is connected and select_clk=1.')
                break
            elif i == 0:
                print('Writing select_clk=1')
                m.write('cc', 'select_clk', [1])
                time.sleep(1)

    else:
        o.error("I do not know how to '%s'" % action)
