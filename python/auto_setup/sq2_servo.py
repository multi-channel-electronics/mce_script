import auto_setup.util as util
from numpy import *
from mce_data import MCERunfile, MCEFile

def smooth(x, scale):
    s = x.shape
    x.shape = (-1, s[-1])
    y = array([convolve(xx, [1]*scale, mode='valid') for xx in x]) / scale
    x.shape = s
    y.shape = s[:-1] + (y.shape[-1],)
    return y

def acquire(tuning, rc, filename=None, fb=None,
            slope=None, bias=None, gain=None):

    # Convert to 0-based rc indices.
    rci = rc - 1

    # File defaults
    if filename == None:
        filename = tuning.get_filename(rc=rc, action='sq2servo')
    try:
        acq_id = int(filename.split('_')[0])
    except ValueError:
        acq_id = 0

    # Biasing semantics are complicated, fix me.
    change_bias = not (bias == False)
    if bias == None and tuning.get_exp_param('sq2_servo_bias_ramp')[0] != 0:
        bias = {}
        for k in ['start','count','step']:
            bias[k] = tuning.get_exp_param('sq2_servo_bias_%s'%k)[0]
    if bias == None or bias == False:
        bias = {'start': tuning.get_exp_param('default_sq2_bias'),
                'count': 1,
                'step': 0 }
    # FB
    if fb == None:
        fb = {}
        for k in ['start','count','step']:
            fb[k] = tuning.get_exp_param('sq2_servo_flux_%s'%k)[0]
    if gain == None:
        gain = tuning.get_exp_param('sq2servo_gain')[rci]
    
    # Execute C servo program
    cmd = [tuning+'/sq2servo', filename,
           bias['start'], bias['step'], bias['count'],
           fb['start'], fb['step'], fb['count'],
           rc, int(change_bias), gain,
           '>>', tuning.log_file]

    ok = tuning.run(cmd)
    if not ok:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.data_dir, filename)
    rf = MCERunfile(fullname)
    n_frames = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2] * \
        rf.Item('par_ramp', 'par_step loop2 par1', type='int')[2]
    
    util.register(acq_id, 'tune_servo', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename':fullname }





def reduce(tuning, sq2file, lock_amp=True, slope=None):
    # Defaults from config file
    if slope == None:
        slope = tuning.get_exp_param('sq2servo_gain')[rci] / \
            tuning.get_exp_param('sq1servo_gain')[rci]
    if not hasattr(sq2file, 'haskey'):
        sq2file = {'filename': sq2file}

    datafile = sq2file['filename']
    rf = MCERunfile(datafile+'.run')
    error, feedback = util.load_bias_file(datafile+'.bias')

    # How many biases is this?
    n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2]
    fb_params = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
    fb_0, d_fb, n_fb = fb_params
    fb = arange(fb_0, n_fb*d_fb+fb_0, d_fb)

    # Assert n_bias * n_fb == feedback.shape[1]

    # Discard leading and trailing samples in each fb ramp
    lo = n_fb / 2
    hi = n_fb * 7 / 8
    scale = n_fb / 40
    yscale = 100             # Tolerance for declaring y-values equal

    # Analyze each bias independently
    for ib in range(n_bias):
        # The signal we will look at
        y = feedback[:,ib*n_fb:(ib+1)*n_fb]

        # Smooth, differentiate, and truncate to same length
        y = smooth(y, scale)
        x_offset = (scale+1)/2      # Later we will compensate
        dy = y[:,1:] - y[:,:-1]
        y = y[:,:-1]

        # Measure y-extent
        y_max, y_min = y[:,lo:hi].max(axis=1), y[:,lo:hi].min(axis=1)
        y_mid, y_amp = (y_max + y_min)/2, (y_max - y_min)/2

        # Find a rising or falling region
        if slope < 0:
            # Position of minimum
            i_min = y[:,lo:hi].argmin(axis=1) + lo
            # Find points with positive derivative, away from extrema
            pos_der = (dy > 0) * (y_max.reshape(-1,1) - y > yscale) * \
                (y - y_min.reshape(-1,1) > yscale)
            # Find right-most such point that is to the left of i_min
            indices = [p[scale:m-scale/2].nonzero()[0] + scale for p,m in zip(pos_der,i_min)]
            # In no solution cases, take left most point.
            for i in range(len(indices)):
                if len(indices[i]) == 0: indices[i] = array([0])
            i_max = array([x[-1] for x in indices])
        else:
            i_max = y[:,lo:hi].argmax(axis=1) + lo
            neg_der = (dy < 0) * (y_max.reshape(-1,1) - y > yscale) * \
                (y - y_min.reshape(-1,1) > yscale)
            indices = [p[scale:m-scale/2].nonzero()[0] + scale for p,m in zip(neg_der,i_max)]
            for i in range(len(indices)):
                if len(indices[i]) == 0: indices[i] = array([0])
            i_min = array([x[-1] for x in indices])

        # Lock in y or x.
        if lock_amp:
            target = array([yy[a] + yy[b] for yy,a,b in zip(y, i_min, i_max)]) / 2
            if slope < 0:
                lock_idx = array([(yy[a:b]-tt<=0).nonzero()[0][0]+a \
                                      for a,b,tt,yy in zip(i_max, i_min, target, y)])
            else:
                lock_idx = array([(yy[a:b]-tt>=0).nonzero()[0][0]+a \
                                      for a,b,tt,yy in zip(i_min, i_max, target, y)])
        else:
            lock_idx = (i_max + i_min)/2
        lock_y = array([yy[i] for i,yy in zip(lock_idx, y)])
        lock_idx += x_offset
        lock_x = fb[lock_idx]
    
    # Save results
    
    results = {'lock_idx': lock_idx,
               'lock_y': lock_y,
               'lock_x': lock_x,
               'slope': slope,
               'left_x': fb[amin(vstack((i_min, i_max)), axis=0)],
               'right_x': fb[amax(vstack((i_min, i_max)), axis=0)],
               }
    return results

def plot(tuning, sq2file, lock_points):
    
    if not hasattr(sq2file, 'haskey'):
        sq2file = {'filename': sq2file}

    datafile = sq2file['filename']
    rf = MCERunfile(datafile+'.run')
    error, servo_val = util.load_bias_file(datafile+'.bias')

    # How many biases is this?
    n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2]
    fb_params = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
    fb_0, d_fb, n_fb = fb_params
    fb = arange(fb_0, n_fb*d_fb+fb_0, d_fb)

    # Plot plot plot
    n_cols = servo_val.shape[0]
    for page in range((n_cols + 7)/8):
        p = util.tuningPlot(4, 2)
        for chan in range(8):
            i = page*8 + chan
            ax = p.subplot(title='Column %i' % i)
            ax.plot(fb/1000., servo_val[i]/1000.)
            ax.axhline(y=lock_points['lock_y'][i]/1000.,c='k')
            ax.axvline(x=lock_points['lock_x'][i]/1000.,c='k')
            ax.axvline(x=lock_points['left_x'][i]/1000.,c='k',ls='dashed')
            ax.axvline(x=lock_points['right_x'][i]/1000.,c='k',ls='dashed')
            p.format()
        p.save('test.png')
        p.save('test.pdf')
        p.save('test.eps')
