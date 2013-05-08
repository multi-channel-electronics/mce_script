#!/usr/bin/python

USAGE="""
%prog [options]

Acquire bias or heater step data, using MCE internal commanding.

This script uses internal MCE ramping to produce a square wave on the
TES (or heater) bias lines.  It will cause the bias to step between

      [ current bias ] and [ current bias + depth ]

To pass an observing log id to the registration program, you can use
the MAS_LOGID environment variable or pass --log-note=xxxx.
"""

from mce_control import mce_control as MCE
import os
import time

from auto_setup.util import mas_path
mas_path = mas_path()

from optparse import OptionParser
o = OptionParser(usage=USAGE)
o.add_option('--filename',help=
             "Filename. If multiple bias cards will be "\
                 "used, the filename must contain one of '%(bias_card)s' or "\
                 "'%(ctime)s', which will be expanded to the bias card name "\
                 "or a ctime so that the output filenames will be unique.")
o.add_option('--bc', action='append', help=
             "Specify a bias card.  Can be passed multiple times, to select "\
                 "multiple cards.  If this is not passed, the step will be "\
                 "run on all bias cards which contribute to the target "\
                 "register.")
             
o.add_option('--depth', type=int, help=
             "Depth of the step, in DAC units.")
o.add_option('--dwell', type=float, help=
             "Dwell time of each level, in seconds.")
o.add_option('--frames', type=int, help=
             "Number of frames to acquire.")
o.add_option('--log-note', help=
             "Data to pass to acquisition register.")
o.add_option('--readout-rounding', default=False, action='store_true', help=
             "Round the stepping rate to be a multiple of the readout rate.")
o.add_option('--data-mode', type=int, default=1, help=
             "Specify data_mode.  Defaults to 1 (unfiltered feedback only). "\
                 "The original data_mode will be restored on exit.")

opts, args = o.parse_args()

# Check and convert options.
if opts.bc == None:
    opts.bc = ['bc1', 'bc2', 'bc3']

#for bc in opts.bc:
#    if bc not in ['bc1', 'bc2'

if opts.filename == None:
    opts.filename = '%(ctime0)s_%(bias_card)s_step'

## We're not ready for this yet...
#if not '/' in opts.filename:
#    # Prepend $MAS_DATA
#    opts.filename = mas_path.data_dir() + '/' + opts.filename

if len(opts.bc) > 1:
    if not (('%(ctime)s' in opts.filename) or 
            ('%(bias_card)s' in opts.filename)):
        raise RuntimeError, "Invalid filename for multiple bias card acq."

if opts.depth == None:
    opts.depth = 50

if opts.dwell == None:
    opts.dwell = 1.0032

if opts.frames == None:
    opts.frames = 10000

if opts.log_note == None:
    opts.log_note = os.getenv('MAS_LOGID', '')


#
# Preparation 
#

mce = MCE()
ctime0 = int(time.time())
data_mode_before = mce.data_mode()

## Get timing and stuff.

readout_rate = mce.readout_rate()
mux_rate = mce.mux_rate()
print 'Internal frame rate is currently %.3f Hz' % mux_rate
print 'Readout rate is %.3f Hz' % readout_rate

dwell_cycles = int(round(opts.dwell * mux_rate))
print 'Requested switching every %i mux cycles' % dwell_cycles
print 'Dwell time is %.4f' % (dwell_cycles / mux_rate)

if opts.readout_rounding:
    data_period = mce.data_rate()
    dwell_cycles = int(round(opts.dwell * readout_rate)) * data_period
    print 'Rounding to %i mux cycles to match data_rate=%i' % \
        (dwell_cycles, data_period)

# Disable MCE internal commanding
#mce_cmd -qx wb cc internal_cmd_mode 0
mce.write('cc', 'internal_cmd_mode', 0)

# Set everything up except ramp_card_addr
## The card and parameter to step can, in principal be extracted from
## mce_status -g output.  For now, we hard code them :O
## Card id's will be 7,8,9 for bc1,2,3.  "mod_val" param is 0x27
##bias_card = int(bc[2]) + 6
##bias_para = 0x27
#
## Set mod_val ramp parameters
##mce_cmd -qx wb cc ramp_param_id  $bias_para
##mce_cmd -qx wb cc ramp_card_addr $bias_card
##mce_cmd -qx wb cc ramp_step_period $step_period
##mce_cmd -qx wb cc ramp_min_val     $bias_lo
##mce_cmd -qx wb cc ramp_max_val     $bias_hi
##mce_cmd -qx wb cc ramp_step_size   $step_depth
## ramp_step_data_num is the number of data to issue per ramp step command
## 1 is right for mod_val.
##mce_cmd -qx wb cc ramp_step_data_num 1

for k, v in [
    #('ramp_card_addr', int(bc[2]) + 6),
    ('ramp_param_id', 0x27),
    ('ramp_step_period', dwell_cycles),
    ('ramp_min_val', 0),
    ('ramp_max_val', opts.depth),
    ('ramp_step_size', opts.depth),
    ('ramp_step_data_num', 1),
    ]:
    mce.write('cc', k, v)

# Use data mode 1, unfiltered 32-bit feedback
#mce_cmd -qx wb rca data_mode 1
mce.data_mode(opts.data_mode)

#
# Run the ramps on each bc.
# 

for bc in opts.bc:
    this_data = {
        'bias_card': bc,
        'ctime': str(int(time.time())),
        'ctime0': str(ctime0),
        'n_frames': opts.frames,
        'log': opts.log_note,
        }
    this_data['filename'] = opts.filename % this_data

    # Zero mod_val and set the mod_val targets:
    #mce_cmd -qx wb bc$bc mod_val 0
    #mce_set_mod_targets tes bias --select bc$bc bias
    mce.write(bc, 'mod_val', [0])
    os.system('mce_set_mod_targets tes bias --select %s bias' % bc)
    
    # Register the acquisition
    #acq_register $ct bias_step $MAS_DATA/$filename $n_points "$MAS_LOGID"
    os.system('acq_register %(ctime)s bias_step %(filename)s '
              '%(n_frames)i "%(log)s"' %
              this_data)
    
    mce.write('cc', 'ramp_card_addr', int(bc[2]) + 6)


    # Enable the ramp and acquire
    #mce_cmd -qx wb cc internal_cmd_mode 2
    mce.write('cc', 'internal_cmd_mode', 2)

    #update_userword s
    # Acquire.
    os.system('mce_run %(filename)s %(n_frames)i s' % this_data)
    
    # Disable ramp, write mod_val to 0 to restore bias.
    #mce_cmd -qx wb cc internal_cmd_mode 0
    #mce_cmd -qx sleep 50000
    #mce_cmd -qx wb bc$bc mod_val 0
    mce.write('cc', 'internal_cmd_mode', 0)
    time.sleep(.05)
    mce.write(bc, 'mod_val', 0)
    
# Restore data_mode
#mce_cmd -qx wb rca data_mode ${last_data_mode[0]}
mce.data_mode(int(data_mode_before))

print 'Finished'

