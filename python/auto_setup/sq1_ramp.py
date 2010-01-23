import os, time
from mce_data import MCEFile, MCERunfile
from numpy import *
import auto_setup.idl_compat as idl_compat
import auto_setup.util as util
import auto_setup.servo as servo

def go(tuning, rc, filename=None, slope=None, flags=None):
    ok, ramp_data = acquire(tuning, rc, filename=filename, do_bias=do_bias)
    if not ok:
        raise RuntimeError, servo_data['error']

    lock_points = reduce(tuning, servo_data, slope=slope)
    plot(tuning, ramp_data, lock_points)

    # Return dictionary of relevant results
    return {'final_sa_bias_ch_by_ch': lock_points['sa_bias'],
            'sa_target': lock_points['lock_y'],
            'sa_fb_init': lock_points['lock_x'],
            }

def acquire(tuning, rc, filename=None, check=False):
    # Convert to 0-based rc indices.
    rci = rc - 1

    # File defaults
    if filename == None:
        action = 'sq1ramp'
        if check: action = 'sq1rampc'
        filename, acq_id = tuning.get_filename(rc=rc, action=action)
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Execute ramp
    cmd = ['ramp_sq1_fb', filename, rc]
    status = tuning.run(cmd)
    if status != 0:
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


def reduce(tuning, ramp_data, slope=None):
    if not hasattr(ramp_data, 'haskey'):
        ramp_data = {'filename': ramp_data,
                     'basename': os.path.split(ramp_data)[-1]
                     }
    datafile = ramp_data['filename']

    # Read data preserving rows/cols dimensioning
    mcefile = MCEFile(datafile)
    data = mcefile.Read(row_col=True).data
    n_cols = data.shape[1]
    n_rows = data.shape[0]

    # But what columns are these exactly?
    rcs = mcefile.runfile.Item('FRAMEACQ', 'RC', type='int')
    cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()

    # Feedback vector.
    fb0, d_fb, n_fb = mcefile.runfile.Item('par_ramp', 'par_step loop1 par1', type='int')
    fb = (fb0 + arange(n_fb) * d_fb)

    # Analyze every single stupid rampc curve
    scale = max([n_fb/40, 1])
    y = servo.smooth(data, scale).reshape(n_rows*n_cols, -1)
    x_offset = scale/2
    dy  = y[:,1:] - y[:,:-1]
    y   = y[:,:-1]

    # Simple way to find local extrema
    Thi = ((dy[:,1:] < 0)*(dy[:,:-1] >= 0))
    Tlo = ((dy[:,1:] > 0)*(dy[:,:-1] <= 0))

    # Indices of extrema, by det.
    Tex = [x.nonzero()[0] for x in Thi+Tlo]

    # Find widest region between extrema
    dT = [ x[1:] - x[:-1] for x in Tex ]
    widx = [ argmax(x) for x in dT ]
    lims = [ (x[i], x[i+1]) for x,i in zip(Tex, widx) ]

    # Compute suggested ADC offset based on these.
    adc_offset = array([(yy[a]+yy[b])/2 for (a,b),yy in zip(lims,y)])
    
    # Good enough
    lock_left, lock_right = array(lims).transpose()
    
    result = {
        'lock_idx': (lock_left + lock_right)/2,
        'left_idx': lock_left,
        'right_idx': lock_right,
        'lock_y': adc_offset,
        }
    for k in ['lock', 'left', 'right']:
        result[k+'_idx'] += x_offset
        result[k+'_x'] = fb[result[k+'_idx']]
    return result



def plot(tuning, ramp_data, lock_points, plot_file=None, format='png'):
    if not hasattr(ramp_data, 'haskey'):
        ramp_data = {'filename': ramp_data,
                      'basename': os.path.split(ramp_data)[-1]}
    if plot_file == None:
        _, basename = os.path.split(ramp_data['filename'])
        plot_file = os.path.join(tuning.plot_dir, '%s_%%02i.%s' % (basename, format))

    # Read data preserving rows/cols dimensioning
    datafile = ramp_data['filename']
    mcefile = MCEFile(datafile)
    data = mcefile.Read(row_col=True).data
    n_cols = data.shape[1]
    n_rows = data.shape[0]

    # But what columns are these exactly?
    rcs = mcefile.runfile.Item('FRAMEACQ', 'RC', type='int')
    columns = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()

    # Feedback vector.
    fb0, d_fb, n_fb = mcefile.runfile.Item('par_ramp', 'par_step loop1 par1', type='int')
    fb = (fb0 + arange(n_fb) * d_fb)

    # Plot plot plot
    servo.plot(fb, data.reshape(-1, n_fb), lock_points, plot_file,
               title=ramp_data['basename'],
               titles=['Row %2i  Column %2i' %(j, i) \
                           for i in columns for j in range(data.shape[0])],
               xlabel='SQ1 FB / 1000',
               ylabel='AD Units / 1000')

