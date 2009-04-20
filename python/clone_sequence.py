"""
Watch for new 'file-sequenced' data files, then hard link them
ordinary-looking data files with names that will fool the rest of the system.
"""

from optparse import OptionParser
from glob import glob
from time import sleep, time
from commands import getstatusoutput
import sys

FRAME_RATE=398.724
MAX_INDEX=1000

def link_file(source, dest):
    s, o = getstatusoutput('ln "%s" "%s"' % (source, dest))
    if s != 0:
        print 'WARNING: Failed to link %s to %s'%(source, dest)
    return s == 0

def new_filename(start, opts, index):
    t = int(start + opts.block_size * index / opts.frame_rate)
    return '%s/%010i_%s' % (opts.output_dir, t, opts.suffix), t

def register_file(filename, frame_count, t, index, opts):
    n = opts.block_size
    if (index+1) * n > frame_count:
        n = frame_count - n * index
    s, o = getstatusoutput('acq_register %i auto %s %i "%s"' % \
                               (t, filename, n, opts.note))
    if s != 0:
        print 'WARNING: DB registration failed for %s'%filename
    return s == 0

if __name__ == '__main__':

    # Options
    o = OptionParser()
    o.add_option('-x','--expire-time',type='int',default=None)
    o.add_option('-u','--update-interval',type='int',default=60)
    o.add_option('-s','--suffix',type='string',default='dat')
    o.add_option('-d','--digits',type='int',default=3)
    o.add_option('-b','--block-size',type='int',default=240000)
    o.add_option('-r','--frame-rate',type='float',default=FRAME_RATE)
    o.add_option('-n','--note',type='string',default='')
    o.add_option('-o','--output-dir',type='string',default='/data/cryo/current_data/')
    opts, args = o.parse_args()

    # Minimal options
    if len(args) != 2:
        print 'ERROR: Arguments are (basename, frame-count).'
        sys.exit(10)
    basename = args[0]
    n_frames = int(args[1])
    
    if opts.expire_time == None:
        # By default, add two minutes grace
        opts.expire_time = (opts.block_size / opts.frame_rate) + 120

    n_block = (n_frames + opts.block_size - 1)/opts.block_size

    # Create template for finding the index files
    template = '%s.%%0%ii' % (basename, opts.digits)
    
    # Record the start time, make sure it's unique (lame)
    start = time()+1

    # Collect files in sequence (starting with runfile)
    index = -1
    idleness = 0
    
    # Main loop
    done = False
    while not done:
        if index < 0:
            files = glob('%s.run'%basename)
        else:
            files = glob(template % index)
        if len(files) > 1:
            print 'ERROR: Multiple matches to "%s" at index %i'%\
                (basename, index)
            index += 1
        elif len(files) == 1:
            if index < 0:
                runfile = files[0]
            else:
                filename, t = new_filename(start, opts, index)
                link_file(files[0],filename)
                link_file(runfile,filename+'.run')
                register_file(filename, n_frames, t, index, opts)
            idleness = 0
            index += 1
        else:
            # Delay before checking again round.
            sleep(opts.update_interval)
            idleness += opts.update_interval
        done = idleness > opts.expire_time or index >= n_block
