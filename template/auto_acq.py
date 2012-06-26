#!/usr/bin/python

import os, sys
import time
import subprocess

from optparse import OptionParser

from auto_setup.util import mas_path

def get_output(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    value = p.communicate()[0]
    return value


mas_path = mas_path()

o = OptionParser()
o.add_option('--no-locking', action='store_true')
o.add_option('--rc', default='s')
opts, args = o.parse_args()

acq_desc = [
    {
        'type': 'flat',
        'sequencing_interval': -1,
        'filename': '%(data_dir)s/%(ctime)s',
        'runfile': 'create',
        },
    {
        'type': 'dirfile',
        'sequencing_interval': -1,
        'filename': '%(data_dir)s/%(ctime)s_df',
        'runfile': 'symlink',
        },
    ]

# Generate filename and stuff
details = {}
details['ctime'] = '%i' % int(time.time())
details['data_dir'] = mas_path.data_dir()
details['n_frames'] = int(args[0])
details['rc'] = 'rc%s' % opts.rc
details['temp_root'] = '%s/%s_%s__' % \
    (mas_path.temp_dir(), get_output('whoami').strip(),
     mas_path.__get_path__('fibre-card',[],None))


# 1. Runfile generation / linking
rf0 = None
for acq in acq_desc:
    rf_type = acq.get('runfile')
    if not rf_type:
        continue
    # Runfile name?
    filename = acq['filename'] % details
    rf_filename = filename + '.run'
    if rf_type == 'create':
        os.system('/bin/bash -c mce_status >> %s' % rf_filename)
        os.system('/bin/bash -c frameacq_stamp %s %s %i >> %s' % \
                  (details['rc'], filename, details['n_frames'], rf_filename))
        if rf0 == None:
            rf0 = rf_filename
    elif rf_type == 'symlink':
        os.symlink(rf0, rf_filename)
    else:
        raise

# 2. Data acquisition init -- construct lines for mce_cmd
lines = []

## We probably want to lock the data driver.
if not opts.no_locking:
    lines.append('lock_down')

## Enable multisync, then add acquisitions.
lines = ['acq_multi_begin']

for acq in acq_desc:
    my_det = details.copy()
    my_det['filename'] = acq['filename'] % my_det
    my_det['seq_int'] = acq.get('sequencing_interval', 0)
    fseq = my_det['seq_int'] > 0
    ftype = acq.get('type','flat')
    if ftype == 'flat':
        line = 'acq_config'
    elif ftype == 'dirfile':
        line = 'acq_config_dirfile'
    else:
        raise
    if my_det['seq_int'] > 0:
        line += 'fs %(filename)s %(rc)s %(seq_int)i' % my_det
    else:
        line += ' %(filename)s %(rc)s' % my_det
    lines.append(line)

## And some frames.
lines.append('acq_go %(n_frames)i' % details)

## Write those to a temp file...
tempfile='%(temp_root)s__mce_run.temp' % details


## Execute carefully...
cmd = ['mce_cmd', '-q']
for line in lines:
    cmd += ['-X', line]

err = subprocess.call(cmd)
if err != 0:
    sys.exit(err)

