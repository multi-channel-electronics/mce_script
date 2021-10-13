#!/usr/bin/python

USAGE="""
%prog [options] n_frames

Acquires data, possibly to multiple files, according to some data
acquisition profile.
"""

import os, sys
import time
import subprocess

from optparse import OptionParser

from auto_setup.util import mas_path
mas_path = mas_path()

def get_output(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    value = p.communicate()[0]
    return value

def is_and_is_symlink(linkname):
    try:
        os.readlink(linkname)
    except:
        return False
    return True

o = OptionParser(usage=USAGE)
o.add_option('--no-locking', action='store_true',
             help="Do not obtain the data lock.")
o.add_option('--rc', default='s',
             help="Select an RC from 1, 2, 3, 4, or s.")
opts, args = o.parse_args()

# Check args
if len(args) < 1:
    o.error('Provide a frame count.')

n_frames = int(args[0])


#
# Descriptions of output files
#

acq_desc = [
    {
        # Example of flatfile acquisition, with static symlink:
        'type': 'flatfile',
        'sequencing_interval': -1,
        'filename': '%(data_dir)s/%(ctime)s_dat',
        'symlink': '%(data_dir)s/mcedata',
        'runfile': 'create',
        },
    {
        # Example of sequenced dirfile acquisition, with a few options:
        'type': 'dirfile',
        'sequencing_interval': 200,
        'filename': '%(data_dir)s/%(ctime)s_df',
        'options': {
            'include': 'path/to/extra_format',
            'runfile': 'include',
            'spf': 400
            },
        'symlink': None,
        'runfile': 'symlink',
        },
    {
        # Example of a command which is just executed by this script:
        'type': 'command',
        'command': 'echo FILENAME=%(data_dir)s/%(ctime)s_dat',
        },
    ]

# Generate filename and stuff
details = {}
details['ctime'] = '%i' % int(time.time())
details['data_dir'] = mas_path.data_dir()
details['n_frames'] = n_frames
details['rc'] = 'rc%s' % opts.rc
details['rc_num'] = '%s' % opts.rc
details['temp_root'] = '%s/%s_%i__' % \
    (mas_path.temp_dir(), get_output('whoami').strip(), mas_path.fibre_card())


# 1. Runfile generation / linking
rf0 = None
for acq in acq_desc:
    rf_type = acq.get('runfile')
    if not rf_type or acq['type'] in ['pass', 'command']:
        continue
    # Runfile name?
    filename = acq['filename'] % details
    rf_filename = filename + '.run'
    if rf_type == 'create':
        os.system('mce_status > %s' % rf_filename)
        os.system('frameacq_stamp %s %s %i >> %s' % \
                  (details['rc_num'], filename, details['n_frames'], rf_filename))
        if rf0 is None:
            rf0 = rf_filename
    elif rf_type == 'symlink':
        if rf0 is None:
            o.error('Need to create a runfile before symlinking one.')
        os.symlink(rf0, rf_filename)
    else:
        raise
    # If data has a symlink, so should the runfile; just append .run
    slink = acq.get('symlink',None)
    if slink is not None and slink != '':
        slink = (slink % details) +'.run'
        if is_and_is_symlink(slink):
            os.remove(slink)
        os.symlink(rf_filename, slink)

# 2. Data acquisition init -- construct lines for mce_cmd
lines = []

## We probably want to lock the data driver.
if not opts.no_locking:
    lines.append('lock_down')

## Enable multisync, then add acquisitions.
lines = ['acq_multi_begin']

acq_idx = 0;
for acq in acq_desc:
    ftype = acq.get('type','flatfile')
    if ftype == 'pass':
        continue

    # Update details
    my_det = details.copy()
    my_det['acq_idx'] = acq_idx;
    my_det['filename'] = acq.get('filename','') % my_det
    my_det['seq_int'] = acq.get('sequencing_interval', 0)
    my_det['incfile'] = details['temp_root'] + ('inc%(acq_idx)i' % my_det)

    # If this is a custom command, execute and continue
    if ftype == 'command':
        os.system(acq['command'] % my_det)
        continue

    # Name any symlink
    slink = acq.get('symlink',None)
    if slink is None or slink == '':
        lines.append('acq_link')
    else:
        lines.append('acq_link %s' % (slink % my_det))

    # Process options
    opts = acq.get('options', None)
    if opts is not None:
        # handle special options
        if ftype == 'dirfile':
            have_incfile = 0
            if ('runfile' in opts):
                if (opts['runfile'] == 'include'):
                    have_incfile = 1
                    # this truncates incfile
                    os.system('mce_status -d > %s' % my_det['incfile'])
                else:
                    o.error("Unknown 'runfile' option: %s" % opts['runfile'])
                
                del opts['runfile']
            if ('include' in opts):
                # truncate, if necessary
                if have_incfile == 0:
                    os.system('echo > %s' % my_det['incfile'])
                # append included file
                os.system('cat %s >> %s' % (opts['include'], my_det['incfile']))
                have_incfile = 1

                del opts['include']
            if (have_incfile):
                opts['include'] = my_det['incfile'];
        
        # pass any remaining options to mce_cmd
        for key,val in list(opts.items()):
            lines.append('acq_option %s %s %s' % (ftype, key, val))

    # Construct init line for this output type
    fseq = my_det['seq_int'] > 0
    if ftype == 'flatfile':
        line = 'acq_config'
    elif ftype == 'dirfile':
        line = 'acq_config_dirfile'
    else:
        raise ValueError("unknown type '%s'" % ftype)
    if my_det['seq_int'] > 0:
        line += '_fs %(filename)s %(rc)s %(seq_int)i' % my_det
    else:
        line += ' %(filename)s %(rc)s' % my_det
    lines.append(line)

    acq_idx = acq_idx + 1;

## And some frames.
lines.append('acq_go %(n_frames)i' % details)

## Execute carefully...
cmd = ['mce_cmd', '-q']
for line in lines:
    cmd += ['-X', line]

err = subprocess.call(cmd)
if err != 0:
    sys.exit(err)

