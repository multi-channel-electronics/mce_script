"""
__main__ style stuff for mux11d tuning.
"""

import util
import series_array
import sq2_servo
import sq1_servo
import sq1_ramp
import rs_servo
import frame_test

import os
import time
import shutil
from numpy import *

from mce_data import MCERunfile

def do_init_mux11d(tuning, tune_data):
    
    # Are we hybrid muxing?  If so, row_order in experiment.cfg, which
    # is a synonym for ac row_order, should be derived from the
    # contents of mux11d_mux_order.  Do this here, so they're always
    # consistent.
    ishybrid = tuning.get_exp_param('mux11d_hybrid_row_select',missing_ok=True)    
    if ishybrid==1:

        # We've been told to hybrid mux.  Better make sure we have all
        # of the variables we need specified to setup hybrid mux.
        # Don't require mux11d_row_select_multipliers right now; will
        # just default to multiplier=1 if user doesn't specify.
        mux11d_row_select_cards=tuning.get_exp_param('mux11d_row_select_cards',missing_ok=False)
        mux11d_row_select_cards_row0=tuning.get_exp_param('mux11d_row_select_cards_row0',missing_ok=False)
        mux11d_ac_idle_row=tuning.get_exp_param('mux11d_ac_idle_row',missing_ok=False)
        mux11d_mux_order=tuning.get_exp_param('mux11d_mux_order',missing_ok=False)
        # If this isn't consistent with mux11d_mux_order, we will overwrite it & warn the user
        row_order=tuning.get_exp_param('row_order',missing_ok=False)

        # Warn the user if lengths of row_order, mux11d_mux_order,
        # row_select, and row_deselect are not the same.  Won't try to
        # correct, but it's likely the MUX is not in a good
        # configuration if this is true.  This also requires these
        # variables be present or crashes.
        if not ( len(row_order) == \
                  len(mux11d_mux_order) == \
                   len(tuning.get_exp_param('row_select',missing_ok=False)) == \
                    len(tuning.get_exp_param('row_deselect',missing_ok=False)) ):
            print """!!! Warning : hybrid muxing w/ different lengths for at least one of
                   row_order, mux11d_mux_order, row_select, and row_deselect in
                   experiment.cfg.  Proceed at your own risk!"""
        
        # Throw an exception if a card is in mux11d_row_select_cards 2x
        if len(mux11d_row_select_cards)!=len(set(mux11d_row_select_cards)):
            raise ValueError, """trying to hybrid mux but there are duplicate entries in mux11d_row_select_cards - not supported."""
        if len(mux11d_row_select_cards_row0)!=len(set(mux11d_row_select_cards_row0)):
            raise ValueError, """trying to hybrid mux but there are duplicate entries in mux11d_row_select_cards_row0 - not supported."""
        # Make sure cards in mux11d_row_select_cards are doable
        if not set(mux11d_row_select_cards).issubset(['ac','bc1','bc2','bc3']):
            raise ValueError, """can't mux on one of the cards in
                                 mux11d_row_select_cards; can only mux on
                                 ['ac','bc1','bc2','bc3']"""
        # Some functionality right now in mas requires the row0s be in strictly ascending order
        if not list(mux11d_row_select_cards_row0)==sorted(list(mux11d_row_select_cards_row0)):
            raise ValueError, """trying to hybrid mux but the entries in mux11d_row_select_cards_row0 must be in strictly ascending order."""
        if len(mux11d_row_select_cards)!=len(mux11d_row_select_cards_row0):
            raise ValueError, """len(mux11d_row_select_cards)!=len(mux11d_row_select_cards_row0) : every card being 
                                 hybrid muxed must be assigned a row0"""
            
        # Make sure user didn't request a starting row0 for a card in another card's block of RSes.
        card_nrs_dict={ 'ac' : 41, 'bc1' : 32, 'bc2' : 32, 'bc3' : 32 }
        for (r0,card) in zip(mux11d_row_select_cards_row0,mux11d_row_select_cards):
            if len(list(set(mux11d_row_select_cards_row0).intersection(range(r0,r0+card_nrs_dict[card]))))>1:
                raise ValueError, """trying to hybrid mux but overlap detected between RS blocks.  Make sure row0's for cards are 
                                     correctly spaced in mux11d_row_select_cards_row0."""
        
        # Make sure there's no RS requested outside of a valid RS block
        for rs in mux11d_mux_order:
            if not any([rs in card_rs_range for card_rs_range in
                        [range(r0,r0+card_nrs_dict[card]) for (r0,card) in
                         zip(mux11d_row_select_cards_row0,mux11d_row_select_cards)]]):
                raise ValueError, """trying to hybrid mux but
                                     requested rs=%d in mux11d_mux_order, but that rs
                                     doesn't fall into any defined hybrid rs block!"""%(rs)

        # Make sure ac idle row is in AC's RS block (ac idle row is indexed from zero, so it's native to ac row_order)
        if mux11d_ac_idle_row not in range(0,41):
            raise ValueError, """trying to hybrid mux but
                                 mux11d_ac_idle_row must be in [0:40]!"""

        # Build ac row_order for experiment.cfg from mux11d_mux_order
        hybrid_ac_row_order=[]
        if 'ac' in mux11d_row_select_cards:
            acr0=mux11d_row_select_cards_row0[where(mux11d_row_select_cards=='ac')]
            acrmax=acr0+(card_nrs_dict['ac']-1)

            for rs in mux11d_mux_order:
                if rs in range(acr0,acrmax+1):
                    # ac row_order knows only the AC RSes.  So they
                    # start at 0, hence the -int(acr0)
                    # acr0 is a (1,) np.array, so cast to int
                    hybrid_ac_row_order.append(rs-int(acr0)) 
                else:
                    # Don't have to subtract acr0 because
                    # mux11d_ac_idle_row is native to ac row_order
                    hybrid_ac_row_order.append(mux11d_ac_idle_row) 
        else:
            # AC is not in the list of cards to hybrid mux on!  That
            # is a little weird but roll with it.  ac row_order is all
            # idle row.  Don't have to subtract acr0 because
            # mux11d_ac_idle_row is native to ac row_order
            hybrid_ac_row_order=[mux11d_ac_idle_row]*len(mux11d_mux_order) 

        # Make sure row_order is consistent with mux11d_mux_order
        if any([hro!=ro for (hro,ro) in zip(hybrid_ac_row_order,row_order)]):
            print """!!! Warning : hybrid muxing but row_order in
                     experiment.cfg not consistent with mux11d_mux_order.  Will
                     overwrite row_order based on mux11d_mux_order."""
            print """!!! hybrid_ac_row_order=',hybrid_ac_row_order"""
            tuning.set_exp_param('row_order', hybrid_ac_row_order)

    # Done w/ special hybrid-mux only setup
    #

def acquire(tuning, rc, filename=None,
            action_name='', bin_name=None):

    # File defaults
    if filename is None:
        filename, acq_id = tuning.filename(rc=rc, action=action_name)
    else:
        try:
            acq_id = str(int(filename.split('_')[0]))
        except ValueError:
            acq_id = str(time.time())

    cmd = [os.path.join(tuning.bin_path, bin_name), '-p', 50, rc, filename]

    status = tuning.run(cmd)
    if status != 0:
        return False, {'error': 'command failed: %s' % str(cmd)}

    # Register this acquisition, taking nframes from runfile.
    fullname = os.path.join(tuning.base_dir, filename)
    rf = MCERunfile(fullname + ".run")
    n_frames = rf.Item('par_ramp', 'par_step loop1 par1', type='int')[2] * \
        rf.Item('par_ramp', 'par_step loop2 par1', type='int')[2]
    
    tuning.register(acq_id, 'tune_servo', fullname, n_frames)
    
    return True, {'basename': acq_id,
                  'filename': fullname }


def do_rs_servo(tuning, rc, rc_indices):
    """
    Do necessary (but not sufficient) setup so that rsservo will
    work.  Run it, analyze, update experiment.cfg
    """
    # Are we hybrid muxing?
    ishybrid = tuning.get_exp_param('mux11d_hybrid_row_select',missing_ok=True)

    # Load the default_row_select.  Someone has to, at some point.
    tuning.copy_exp_param('default_row_select', 'row_select')
    tuning.copy_exp_param('default_row_deselect', 'row_deselect')

    # Also load default sq1_bias and make sure it will apply in
    # fast-switching mode as well.
    sq1_bias = tuning.get_exp_param('default_sq1_bias')
    nr = tuning.get_exp_param('array_width') # number of rows sq1_bias_set
    bias_set = tuning.get_exp_param('sq1_bias_set').reshape(-1, nr).\
        transpose() # r,c
    nc = min(len(sq1_bias), bias_set.shape[1])
    bias_set[:,:nc] = sq1_bias[:nc]
    tuning.set_exp_param('sq1_bias', sq1_bias)
    tuning.set_exp_param('sq1_bias_set', bias_set.transpose().ravel())

    optimize = tuning.get_exp_param('optimize_rowsel_servo')
    if optimize == -1:
        # Don't run it, but set the SQ1 bias muxing
        tuning.copy_exp_param("default_config_fast_sq1_bias", "config_fast_sq1_bias", default=1)
        tuning.write_config()
        return

    # Prepare for servo
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
    tuning.copy_exp_param('default_sq1_bias', 'sq1_bias')
    tuning.copy_exp_param('default_sq1_bias_off', 'sq1_bias_off')
    tuning.set_exp_param("config_adc_offset_all", 0)
    tuning.set_exp_param("config_fast_sq1_bias", 0)
    tuning.set_exp_param("config_fast_sa_fb", 1)
    tuning.write_config()

    if len(rc) != 1:
        raise ValueError, "this module does not support weird multi-rc tunes"
        
    ok, servo_data = acquire(tuning, rc[0], action_name='rsservo',
                             bin_name='rs_servo')

    if not ok:
        raise RuntimeError, servo_data['error']

    sq = rs_servo.RSServo(servo_data['filename'], tuning=tuning)
    bias_ramp = sq.bias_style == 'ramp'

    # If multi-bias, plot each one.
    if bias_ramp and tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])

    if bias_ramp:
        sq.reduce1()
        sq = sq.select_biases() # best bias?

    sq_data = sq.reduce()
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])

    # Primary purpose here is to set the row select feedbacks
    new_rsel1 = sq.fb[sq_data['sel_idx_row']]
    new_rsel0 = sq.fb[sq_data['desel_idx_row']]

    if not sq.super_servo:
        n_rs = len(tuning.get_exp_param('row_select'))
        new_rsel1 = [new_rsel1[0]] * n_rs
        new_rsel0 = [new_rsel0[0]] * n_rs

    # Apply rs multiplier (lives in RSServo)
    if ishybrid==1 and sq.hybrid_rs_multipliers is not None:
        new_rsel1 = [nrs1*hrsmult for (nrs1,hrsmult) in
                     zip(new_rsel1,sq.hybrid_rs_multipliers)]
        new_rsel0 = [nrs0*hrsmult for (nrs0,hrsmult) in
                     zip(new_rsel0,sq.hybrid_rs_multipliers)]

    if optimize == 1:
        tuning.set_exp_param('row_select', new_rsel1)
        tuning.set_exp_param('row_deselect', new_rsel0)
        
    # Update per-det SQ1 biases with chosen values from this run
    cols = sq.cols
    if sq.bias_assoc == 'rowcol':
        new_bias = sq.bias.reshape(sq.data_shape[:2])
        bias_set[:new_bias.shape[0],cols] = new_bias
    elif sq.bias_assoc == 'col':
        # Write this single bias for each column to all rows
        bias_set[:,cols] = sq.bias
    else:
        raise HowDidThisHappen

    if optimize == 1:
        tuning.set_exp_param('sq1_bias_set', bias_set.transpose().ravel())

    # Enable fast switching (if enabled in experiment.cfg)
    tuning.copy_exp_param("default_config_fast_sq1_bias", "config_fast_sq1_bias", default=1)

    tuning.write_config()
    return 0


def do_sq1_servo_sa(tuning, rc, rc_indices):
    """
    Do necessary (but not sufficient) setup so that sq1_servo_sa will
    work.  Run it, analyze, update experiment.cfg
    """
    tuning.set_exp_param("data_mode", 0)
    tuning.set_exp_param("servo_mode", 1)
#    tuning.copy_exp_param('default_sq1_bias', 'sq1_bias')
#    tuning.copy_exp_param('default_sq1_bias_off', 'sq1_bias_off')
    tuning.set_exp_param("config_adc_offset_all", 0)
#    tuning.set_exp_param("config_fast_sq1_bias", 0)
    tuning.set_exp_param("config_fast_sa_fb", 1)
    # If we're to ramp the bias, turn off fast biasing.
    if tuning.get_exp_param("sq1_servo_bias_ramp") == 1:
        tuning.set_exp_param("config_fast_sq1_bias", 0)

    tuning.write_config()

    if len(rc) != 1:
        raise ValueError, "this module does not support weird multi-rc tunes"

    ok, servo_data = acquire(tuning, rc[0], action_name='sq1servo_sa',
                             bin_name='sq1servo_sa')

    if not ok:
        raise RuntimeError, servo_data['error']

    sq = sq1_servo.SQ1ServoSA(servo_data['filename'], tuning=tuning)
    bias_ramp = sq.bias_style == 'ramp'

    # If multi-bias, plot each one.
    if bias_ramp and tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])

    if bias_ramp:
        sq.reduce1()
        sq = sq.select_biases(assoc='rowcol') # best bias?

    sq1_data = sq.reduce()
    if tuning.get_exp_param('tuning_do_plots'):
        plot_out = sq.plot()
        tuning.register_plots(*plot_out['plot_files'])
        plot_out = sq.plot_error()
        tuning.register_plots(*plot_out['plot_files'])


    # Load existing bias choices
    nr = tuning.get_exp_param('array_width') # number of rows sq1_bias_set
    bias_set = tuning.get_exp_param('sq1_bias_set').reshape(-1, nr).\
        transpose() # r,c

    # Update per-det SQ1 biases with chosen values from this run
    cols = sq.cols
    if sq.bias_assoc == 'rowcol':
        new_bias = sq.bias.reshape(sq.data_shape[:2])
        bias_set[:new_bias.shape[0],cols] = new_bias
    elif sq.bias_assoc == 'col':
        # write this single bias for each column to all rows
        bias_set[:,cols] = sq.bias
    else:
        raise HowDidThisHappen

    # Enable fast switching (if enabled in experiment.cfg)
    tuning.set_exp_param('sq1_bias_set', bias_set.transpose().ravel())
    tuning.copy_exp_param("default_config_fast_sq1_bias", "config_fast_sq1_bias", default=1)
    super_servo = tuning.get_exp_param('config_mux11d_all_rows')
    fb_set = tuning.get_exp_param('sa_fb_set').reshape(-1, nr).\
        transpose() # r,c

    fb_col = tuning.get_exp_param('sa_fb')
    
    # Determine the SA FB for each column, and if possible for each detector.
    cols = sq.cols
    phi0 = tuning.get_exp_param('sa_flux_quanta')[cols]
    phi0[phi0<=0] = 65536 # kill empty flux_quanta
    if super_servo:
        n_row, n_col = sq.data_shape[-3:-1]
        fb_set[:n_row,cols] = sq1_data['lock_y'].reshape(-1, n_col) % phi0
        # Get chosen row on each column
        rows = tuning.get_exp_param('mux11d_row_choice')[cols]
        fb_col[cols] = array([ fb_set[r,c] for r,c in zip(rows, cols) ]) % phi0
    else:
        # Analysis gives us SA FB for chosen row of each column.
        fb_col[cols] = sq1_data['lock_y'] % phi0
        n_row = tuning.get_exp_param('default_num_rows')
        fb_set[:,cols] = sq1_data['lock_y'] % phi0
        
    # Save results, but remove flux quantum
    tuning.set_exp_param('sa_fb', fb_col)
    tuning.set_exp_param('sa_fb_set', fb_set.transpose().ravel())

    tuning.write_config()
    return 0
