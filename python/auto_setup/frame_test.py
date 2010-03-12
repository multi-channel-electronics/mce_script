import os, time
from mce_data import MCEFile, MCERunfile
from numpy import *
import auto_setup.idl_compat as idl_compat
import auto_setup.util as util
import auto_setup.servo as servo

def go(tuning, rc, filename=None):
    ok, frametest = acquire(tuning, rc, filename=filename)
    if not ok:
        raise RuntimeError, frametest['error']

    lockflags = reduce(tuning, frametest)
    plot(tuning, frametest, lockflags)

    # Return dictionary of relevant results
    return {'lockflag': lockflags['flag']
            }

def acquire(tuning, rc=None, filename=None,
            data_mode=4):
    if rc == None:
        rc = 'rcs'

    # File defaults
    if filename == None:
        action = 'lock'
        filename, acq_id = tuning.get_filename(rc=rc, action=action)
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Set data mode and acquire
    cmd = ('mce_cmd -x wb %s data_mode %i' % (rc, data_mode)).split()
    if tuning.run(cmd) != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}
    cmd = ['mce_run', file_name, npts, rc[-1]]
    if tuning.run(cmd) != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.data_dir, filename)
    rf = MCERunfile(fullname)
    n_frames = rf.Item('FRAMEACQ','DATA_FRAMECOUNT',type='int',array=False)
    util.register(acq_id, 'tune_ramp', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename':fullname,
                  'rc': rc,
                  }
    
def reduce(tuning, frametest):
    """
    Just check for unlocked pixels, return ok flags.
    """
    if not hasattr(frametest, 'haskey'):
        frametest = {'filename': frametest,
                     'basename': os.path.split(frametest)[-1]
                     }
    datafile = frametest['filename']

    # Read data preserving rows/cols dimensioning
    mcefile = MCEFile(datafile)
    print mcefile.data_mode
    data = mcefile.Read(field='error',row_col=True)
    data = data.data
    n_cols = data.shape[1]
    n_rows = data.shape[0]
    data.shape = (n_cols*n_rows, -1)

    # But what columns are these exactly?
    rcs = mcefile.runfile.Item('FRAMEACQ', 'RC', type='int')
    cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()

    # Mean error should be way less than RMS
    n = data.shape[-1]
    sigma = std(data,axis=1)
    level = mean(data, axis=1)
    flag = abs(level) < sigma * 10
    flag.shape = (n_rows, n_cols)

    return {
        'flag': flag
        }


def plot(tuning, frametest, lockflags, plot_file=None, format='png'):
    import biggles
    pl = biggles.FramedPlot()
    f = lockflags['flag']
    for m, s in [(f, 'filled circle'),
                 (~f, 'diamond')]:
        j, i = m.nonzero()
        b = biggles.Points(i,j)
        b.style(type=s)
        pl.add(b)
    pl.x.label = 'Column'
    pl.y.label = 'Row'
    pl.save(plot_file)
    
