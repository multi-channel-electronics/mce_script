from numpy import *
import glob
import pylab as pl
import sys
sys.path.append('/home/mhasse/code/MCE/mce_script/branch/py_auto_setup/python')
import auto_setup as aset

def osh(x):
    return x.reshape(33,32)

def atshow(*args, **kwargs):
    if not kwargs.has_key('interpolation'):
        kwargs['interpolation'] = 'nearest'
    if not kwargs.has_key('extent'):
        kwargs['extent'] = (0,32,33,0)
    cbar = True
    if kwargs.has_key('cbar'):
        cbar = kwargs.pop('cbar')
    z = pl.imshow(*args, **kwargs)
    if cbar:
        pl.colorbar()


import optparse
o = optparse.OptionParser()
o.add_option('--output-dir',default='./')
o.add_option('--dead-dir',default=None)
o.add_option('--dead-tags',default=None)
o.add_option('--target', default=None,
             help='Tuning stage to plot; e.g. "sq1_ramp", "sq1_ramp_check"')
opts, args = o.parse_args()

# 
if len(args) == 1 and os.path.isdir(args[0]):
    fs = aset.util.FileSet(folder)
    # Join all RCs
    sq1_set = [aset.SQ1Ramp(fs['sq1_ramp_check']['RC%i'%i]) for i in range(1,5)]
    sq1 = aset.SQ1Ramp.join(sq1_set, base)
else:
    sq1= aset.SQ1Ramp(args[0])

if opts.dead_dir != None:
    if opts.dead_tags == None:
        opts.dead_tags = glob.glob('%s/dead_*.cfg')
        opts.dead_tags = [x.split('/')[-1][5:-4] for x in opts.dead_tags]
    else:
        opts.dead_tags = opts.dead_tags.split(',')
    dead_masks = [aset.util.DeadMask('%s/dead_%s.cfg' % (opts.dead_dir,x), label=x) \
                      for x in opts.dead_tags]
else:
    dead_masks = None

# Restore targets
sq1.reduce1()
sq1.analysis['lock_y'][:] = 0
sq1.reduce2()

sq1.plot(plot_file='%s/%s_' % (opts.output_dir, opts.target, dead_masks=dead_masks))


