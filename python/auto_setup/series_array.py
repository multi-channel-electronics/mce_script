# This is a semitranslation of the IDL auto_setup_squids program.  The
# intent is to separate that program into three broad parts:
#
#  1) Data acquisition
#  2) Data Reduction and Tuning Calculations
#  3) Reporting (ie. Plots &c.)
#
# Because necessary data is stored after each of the above steps, it is 
# possible to run only part of the procedure, if the location of the output
# of previous step(s) is provided.

# -- Handy ruler ------------------------------------------------------|

import os, time
from mce_data import MCEFile, MCERunfile
from numpy import *
import auto_setup.idl_compat as idl_compat
import auto_setup.util as util
import auto_setup.servo as servo

def go():
    pass

def acquire(tuning, rc, filename=None, do_bias=None):
    # Convert to 0-based rc indices.
    rci = rc - 1

    # File defaults
    if filename == None:
        filename, acq_id = tuning.get_filename(rc=rc, action='ssa')
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    # Bias ramp default
    if do_bias == None:
        do_bias = tuning.get_exp_param('sa_ramp_bias')
        
    # Execute ramp
    cmd = ['ramp_sa_fb', filename, rc, int(do_bias)]
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
                  'do_bias': do_bias,
                  }


def reduce(tuning, ramp_data, slope=None):
    if not hasattr(ramp_data, 'haskey'):
        ramp_data = {'filename': ramp_data,
                     'basename': os.path.split(ramp_data)[-1]
                     }
    datafile = ramp_data['filename']
    rf = MCERunfile(datafile + '.run')
    n_frames = rf.Item("FRAMEACQ", "DATA_FRAMECOUNT", type="int", array=False)

    # List RCs and columns involved here...
    rcs = rf.Item('FRAMEACQ', 'RC', type='int')
    cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()

    # Convert to 1 slope per column
    if slope == None:
        slope = tuning.get_exp_param('sq2servo_gain')
    if not hasattr(slope, '__getitem__'): slope = [slope]*4
    if len(slope) < 8:
        slope = (zeros((8,len(slope))) + slope).ravel()
    slope = slope[cols]

    # Read data preserving rows/cols dimensioning
    data = MCEFile(datafile).Read(row_col=True).data
    n_cols = data.shape[1]

    bias_ramp = (rf.Item('par_ramp', 'par_title loop1 par1', array=False).strip() == 'sa_bias')
    
    if bias_ramp:
        bias0, d_bias, n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
        sa_bias = array([bias0 + d_bias*arange(n_bias) for i in range(n_cols)])
        fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
    else:
        # If we weren't ramping the SA bias, we need to know what it was.
        n_bias = 1
        sa_bias = array([rf.Item('HEADER', 'RB sa bias', 'int')[cols]])
        fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')

    # Feedback vector.
    fb = (fb0 + arange(n_fb) * d_fb)

    # Average over rows and expand factor time into (bias x fb)
    av_vol = mean(data.astype('float'), axis=0).reshape(n_cols,n_bias,n_fb)

    if bias_ramp:
        # If this was a bias ramp, choose the best bias.
        amps = amax(av_vol, axis=2) - amin(av_vol, axis=2)
        bias_idx = argmax(amps, axis=1)
    else:
        amps = None
        bias_idx = [0] * n_cols

    # Store SA bias results
    result = {
        'sa_bias_idx': bias_idx,
        'sa_bias': array([s[i] for s,i in zip(sa_bias, bias_idx)]),
        'sa_bias_merit': amps,
        }
    
    # Analyze the 'best' SA curves for lock-points
    scale = max([8 * n_fb / 400, 1])
    y = servo.smooth(array([d[i] for d,i in zip(av_vol, bias_idx)]), scale)
    print av_vol.shape, y.shape
    x_offset = scale/2
    dy = y[:,1:] - y[:,:-1]
    y = y[:,:-1]

    lock_idx, left_idx, right_idx = [], [], []
    for yy, ddy, s in zip(y, dy, slope):
        # Find position of an SA minimum.  Search range depends on desired
        # locking slope because we will eventually need to find an SA max.
        if (s > 0):
            min_start = scale * 4
            min_stop = n_fb * 5 / 8
        else:
            min_start = n_fb * 3 / 8
            min_stop = n_fb - scale * 4

        ind_min = yy[min_start:min_stop].argmin() + min_start

        # Now track to the side, waiting for the slope to change.
        if (s > 0):
            start = ind_min + scale * 2
            stop = len(ddy)
            step = 1
        else:
            start = ind_min - 2 * scale
            stop = -1
            step = -1
          
        idx = arange(start,stop,step)
        slope_change = (ddy * s < 0)[idx].nonzero()[0]
        if len(slope_change)==0:
            ind_max = stop - step
        else:
            ind_max = idx[slope_change.min()]

        # Lock on half-way point between minimum and maximum
        lock_idx.append((ind_min+ind_max)/2)
        left_idx.append(min(ind_max,ind_min))
        right_idx.append(max(ind_max,ind_min))

    lock_y = array([yy[i] for i,yy in zip(lock_idx, y)])
    for x in ['lock_idx', 'left_idx', 'right_idx']:
        exec('%s = array(%s) + x_offset' % (x,x))
    result.update({
            'lock_idx': lock_idx,
            'lock_y': lock_y,
            'slope': slope,
            'left_idx': left_idx,
            'right_idx': right_idx,
            })
    # Add feedback keys
    for k in ['lock', 'left', 'right']:
        result[k+'_x'] = fb[result[k+'_idx']]
    return result

def pasdfasdfsdf():

    if ramp_bias:
        # Make an n_bias + 1 pages set of plots.

        plot_file = directory + "analysis/" + file_name + "_ssa.ps"

        for m in range(n_bias):
            sa_bias = numpy.zeros(8) + bias_start + m * bias_step
            page_label = "%s = %i" % (vert_label, sa_bias)
            for j in range(8):
                # Plot error bars if keyword set.  Error bars are value +- stdev
                if (errors):
                    numpy.errorbar(i_fb, av_vol[m, ..., j],
                        yerr=dev_vol[i, ...])
                else:
                    numpy.plot(i_fb, av_vol[m, ..., j])
                numpy.xlabel(horiz_label + i_units)
                # IDL's ytitle
                numpy.figtext(0,0.5,"Output Voltage" + v_units,
                    rotation='vertical', ha='center', va='center')
                numpy.suptitle("RC%i SA Ch %i   peak-to-peak=%g" % (card, j,
                    estim_range[m,j]))

            numpy.figtext(0, 1, full_name) # Print filename as title
            numpy.figtext(0.6, 1, page_label) # Print SA_BIAS on title line

        # Merit function calculated from the peak-to-peak values
        for chan in range(8):
            numpy.plot((bias_start + arange(n_bias) * bias_step) / 1000.,
                    estim_range[...,chan])
            numpy.xtitle('sa_bias (/1000)')
            numpy.ytitle('peak-to-peak')
            numpy.suptitle('Series Array Channel %i   Card %i' % (chan, card))

        numpy.figtext(0, 1, full_name)
        numpy.figtext(0.6, 1, 'Merit function: peak-to-peak')

    for chan in range(8):
        ind[chan] = estim_range[...,chan].argmax() # method: peak-to-peak

    if (not quiet):
        print """
###########################################################################
SA bias and target (adc_offset) channel by channel:
###########################################################################
  Channel Bias@step (index) Target@half  sa_fb@half 
---------------------------------------------------
        """

    for chan in range(8):
        # MFH - This effective scale is inherited from the original 400 code.
        scale = 5 * n_fb / 400.;
        if scale < 1:
            scale = 1

        deriv_av_vol = idl_compat.deriv(i_fb,
                idl_compat.smooth(av_vol[ind[chan], ..., chan], scale))
        final_sa_bias_ch_by_ch[chan] = round(bias_start + ind[chan] * bias_step)

        # Find position of an SA minimum.  Search range depends on desired
        # locking slope because we will eventually need to find an SA max.
        if (s > 0):
            min_start = scale * 4
            min_stop = n_fb * 5 / 8
        else:
            min_start = n_fb * 3 / 8
            min_stop = n_fb - scale * 4

#        ind_min = [ind[chan],min_start:min_stop,chan].argmin() + min_start

        # Now track to the side, waiting for the slope to change.
        if (slope > 0):
            start = ind_min + scale * 2
            stop = n_fb
            step = 1
        else:
            start = ind_min - 2 * scale
            stop = -1
            step = -1
          
        idx = start + step * numpy.arange((stop - start) * step)
        slope_change = numpy.argwhere(deriv_av_vol[idx] * slope < 0)

        if (slope_change.size == 1):
            ind_max = stop - step
        else:
            ind_max = idx[slope_change.min()]

        # Lock on half-way point between minimum and maximum
        ind_half_point = round(0.5 * (ind_min + ind_max))
        target_half_point_ch_by_ch[chan] = round(1000. * av_vol[ind[chan],
            ind_half_point,chan])
        fb_half_point_ch_by_ch[chan] = round(1000. * i_fb[ind_half_point])

        if (not quiet):
            print "%4i %11i %8i %12i %12i" % (chan,
                final_sa_bias_ch_by_ch[chan], ind[chan],
                target_half_point_ch_by_ch[chan],
                fb_half_point_ch_by_ch[chan])

    SA_target = target_half_point_ch_by_ch
    SA_fb_init = fb_half_point_ch_by_ch

    if (ramp_bias):
        for chan in range(8):
            if ((final_sa_bias_ch_by_ch[chan] > 65535) or
                    (final_sa_bias_ch_by_ch[chan] <= 0)):
                if (not quiet):
                    print """
###########################################################################

WARNING: SA bias of channel """, chan, """ has been set to zero bacause
                  the program found a non valid value

###########################################################################
                    """
                else:
                    print "%s: SA bias of channel %i is invalid (%i), setting to 0" % \
                            (__name__, chan, final_sa_bias_ch_by_ch[chan])
                final_sa_bias_ch_by_ch[chan] = 0
                ind[chan] = 0
            if ((SA_fb_init[chan] > 65536) or (SA_fb_init[chan] <= 0)):
                if (not quiet):
                    print """
###########################################################################

WARNING: SA fb of channel """, chan, """ found on the SA V-phi curve has
                  been set to 32000 bacause the program found a non valid value

###########################################################################
                    """
                else:
                    print "%s: SA fb of channel %i is invalid (%i), setting to 0" % \
                            (__name__, chan, SA_fb_init[chan])
                SA_fb_init[chan] = 32000

    return {"final_sa_bias_ch_by_ch": final_sa_bias_ch_by_ch,
            "SA_target": SA_target,
            "SA_fb_init": SA_fb_init}


def load_ramp_data(filename, reduce=False):
    m = MCEFile(filename)
    rf, data = m.runfile, m.Read(row_col=True).data
    n_cols = data.shape[1]

    bias_ramp = (rf.Item('par_ramp', 'par_title loop1 par1', array=False).strip() == 'sa_bias')
    if bias_ramp:
        bias0, d_bias, n_bias = rf.Item('par_ramp', 'par_step loop1 par1', type='int')
        sa_bias = array([bias0 + d_bias*arange(n_bias) for i in range(n_cols)])
        fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop2 par1', type='int')
    else:
        # If we weren't ramping the SA bias, we need to know what it was.
        n_bias = 1
        sa_bias = array([rf.Item('HEADER', 'RB sa bias', 'int')[cols]])
        fb0, d_fb, n_fb = rf.Item('par_ramp', 'par_step loop1 par1', type='int')

    # List RCs and columns involved here...
    rcs = rf.Item('FRAMEACQ', 'RC', type='int')
    cols = array([i+(rc-1)*8 for i in range(8) for rc in rcs]).ravel()

    # Feedback vector.
    fb = (fb0 + arange(n_fb) * d_fb)

    data = data.reshape(-1, n_cols, n_bias, n_fb)
    if reduce:
        data = mean(data, axis=0)
    return data, sa_bias, fb, bias_ramp, cols


def plot(tuning, ramp_data, lock_points, plot_file=None, format='pdf'):
    
    if not hasattr(ramp_data, 'haskey'):
        ramp_data = {'filename': ramp_data,
                      'basename': os.path.split(ramp_data)[-1]}
    if plot_file == None:
        _, basename = os.path.split(ramp_data['filename'])
        plot_file = os.path.join(tuning.plot_dir, '%s.%s' % (basename, format))

    datafile = ramp_data['filename']
    data, sa_bias, fb, bias_ramp, columns = load_ramp_data(datafile, reduce=True)
    
    # Focus on our chosen bias...
    if bias_ramp:
        data = array([d[i] for d,i in zip(data, lock_points['sa_bias_idx'])])

    # Plot plot plot
    servo.plot(fb, data, lock_points, plot_file,
               title=ramp_data['basename'],
               titles=['Column %i - SA_bias=%6i' %(c,b) \
                           for c,b in zip(columns, lock_points['sa_bias'])],
               xlabel='SA FB / 1000',
               ylabel='AD Units / 1000')

