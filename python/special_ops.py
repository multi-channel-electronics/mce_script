usage="""
%prog [options] action [action, ...]

Recognized actions:

 measure_sa_offset_ratio

   Measure the ADC response to changes in SA bias and SA offset and
   estimate an appropriate value to use for sa_offset_bias_ratio.

"""

from mce_control import mce_control as mce

# Kinds of readout card

class RC_revE:
    # Overall gain of SA output to ADC input
    output_gain = 202.36
    # SA output voltage per ADC bit
    dVdX_adc = 1.8/2**14 / 202.36
    # SA output voltage per bit of offset DAC
    dVdX_offset = 2.5/2**16 / 45.92
    # SA bias voltage, per bit of bias DAC
    dVdX_bias = 2.5/2**16
    # SA bias resistance (not including cable)
    R_bias = 15000.

class RC_revB:
    # Overall gain of SA output to ADC input
    output_gain = 99.46
    # SA output voltage per ADC bit
    dVdX_adc = 1.0/2**14 / 99.46
    # SA output voltage per bit of offset DAC
    dVdX_offset = 2.5/2**16 / 33.90
    # SA bias voltage, per bit of bias DAC
    dVdX_bias = 2.5/2**16
    # SA bias resistance (not including cable)
    R_bias = 15000.



from  optparse import OptionParser

o = OptionParser(usage=usage)
opts, args = o.parse_args()


for action in args:
    if action == 'measure_sa_offset_ratio':
        m = mce()
        print 'Saving current configuration...'
        sa_bias0 = m.read('sa', 'bias')
        sa_offset0 = m.read('sa', 'offset')
        sample_num = m.read('rca', 'sample_num')[0]
        servo0, data0 = m.servo_mode(), m.data_mode()
        
        print 'Setting up...'
        n_sa = len(sa_bias0)
        m.servo_mode(0)
        m.data_mode(0)

        print 'Measuring SA bias response...'
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

        print 'Restoring...'
        m.write('sa', 'offset', sa_offset0)
        m.write('sa', 'bias', sa_bias0) 
        m.servo_mode(servo0)
        m.data_mode(data0)
        
        # Measure response to SA bias:
        d_bias   = (y1 - y0).astype('float') / step / sample_num
        #d_offset = y1 - y2
        ## This is better because it catches open circuits
        d_offset = (y0 - y3).astype('float') / step / sample_num
        ratio = d_bias.astype('float') / d_offset
        if any(d_offset==0):
            ratio[d_offset==0] = 0
        
        print 'SA response (dADC/dBIAS), by column:'
        for r in range((n_sa+7)/8):
            print '  ', ' '.join(['%7.3f' % x
                                  for x in d_bias[r*8:(r+1)*8]])
        print

        print 'Offset response (dDC/dOFFSET), by column:'
        for r in range((n_sa+7)/8):
            print '  ', ' '.join(['%7.3f' % x
                                  for x in d_offset[r*8:(r+1)*8]])
        print

        # Analyze those signals
        rc = RC_revE()
        d_offset_pred = rc.dVdX_offset / rc.dVdX_adc

        # Convert d_bias to voltage ratio between SA output (at
        # pre-amp input) and SA bias (at DAC output)
        dVdV_bias = (d_bias * rc.dVdX_adc / rc.dVdX_bias)**-1
        ## Using R_bias, determine R_cable.
        R_cable = rc.R_bias / (dVdV_bias - 1)

        ## Flags
        offset_good = abs(d_offset/d_offset_pred - 1) < .01

        print 'Estimated SA cable resistance (assumes revE readout card):'
        for r in range((n_sa+7)/8):
            print '  ', ' '.join(['%7.1f' % x for x in R_cable[r*8:(r+1)*8]])
        print


        print 'Apparent resistance ratios, by column:'
        for r in range((n_sa+7)/8):
            print '  ', ' '.join(['%7.3f' % x for x in ratio[r*8:(r+1)*8]])
        ratio_mean = ratio[ratio!=0].mean()
        print 'The typical ratio is:  %.3f' % ratio_mean

        # This ratio isn't necessarily what you want to use, you might
        # want to let the floor drop out gradually
        sa_max = 64000. / step
        sa_fall = -8000*sample_num - y0
        ratio1 = -(sa_fall / sa_max - d_bias) / d_offset
        ratio1[d_offset==0] = 0.
        print 'Suggested sa_offset_bias_ratios, by column:'
        for r in range((n_sa+7)/8):
            print '  ', ' '.join(['%6.3f' % x for x in ratio1[r*8:(r+1)*8]])
        ratio1_min = ratio1[ratio1!=0].min()
        print 'Smallest range-filling ratio: %.3f' % ratio1_min 
        # Rough badness diagnostic
        if ratio1_min < ratio_mean:
            print 'You have weird ratios.  Seek advice.'
        print 'Recommended sa_offset_bias_ratio: %.3f' % ratio1_min

    else:
        o.error("I do not know how to '%s'" % action)
