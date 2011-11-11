usage="""
%prog [options] action [action, ...]

Recognized actions:

 measure_sa_offset_ratio

   Measure the ADC response to changes in SA bias and SA offset and
   estimate an appropriate value to use for sa_offset_bias_ratio.

"""

from mce_control import mce_control as mce

from  optparse import OptionParser

o = OptionParser(usage=usage)
opts, args = o.parse_args()


for action in args:
    if action == 'measure_sa_offset_ratio':
        m = mce()
        print 'Storing SA bias...'
        sa_bias0 = m.read('sa', 'bias')
        sa_offset0 = m.read('sa', 'offset')
        
        print 'Measuring SA bias response...'
        n_sa = len(sa_bias0)
        step = 1000
        m.write('sa', 'bias', [0]*n_sa)
        m.write('sa', 'offset', [0]*n_sa)
        y0 = m.read_row()
        
        m.write('sa', 'bias', [step]*n_sa)
        y1 = m.read_row()
        
        m.write('sa', 'offset', [step]*n_sa)
        y2 = m.read_row()
        
        m.write('sa', 'offset', sa_offset0)
        m.write('sa', 'bias', sa_bias0) 
        
        # Measure response to SA bias:
        d_bias   = y1 - y0
        d_offset = y1 - y2
        ratio = d_bias.astype('float') / d_offset
        if any(d_offset==0):
            ratio[d_offset==0] = 0
        
        print 'Apparent sa_offset_bias_ratios, by column: '
        for r in range((n_sa+7)/8):
            print '  ', ' '.join(['%6.3f' % x for x in ratio[r*8:(r+1)*8]])
        print 'So you probably want to use:  %.3f' % ratio[ratio!=0].mean()
        
    else:
        o.error("I do not know how to '%s'" % action)
