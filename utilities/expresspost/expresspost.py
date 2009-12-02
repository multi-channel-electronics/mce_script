#!/usr/bin/python

import sys, os, time
from glob import glob
import stat
import optparse

class WatchSet:
    """Track a set of files matching a certain pattern."""
    state_New = 10
    state_Done = 20

    def __init__(self, base_dir, pattern, recursive = False,
                 match_dirs = True, match_files = True):
        self.base_dir = base_dir
        self.pattern = pattern
        self.recursive = recursive
        self.match_dirs = match_dirs
        self.match_files = match_files
        self.files = []
        self.states = []

    def SearchCallback(self, arg, dir, files):
        for f in files:
            if f == self.pattern:
                self.matches.append(dir + '/' + f)

    def Search(self, new_only = False):
        self.matches = []
        if (self.recursive):
            os.path.walk(self.base_dir, self.SearchCallback, 0)
        else:
            self.matches = glob(self.base_dir + '/' + self.pattern)
        for m in self.matches:
            if m in self.files:
                continue
            s = os.stat(m)
            d = stat.S_ISDIR(s[stat.ST_MODE])
            if (d and not self.match_dirs) or (not d and not self.match_files):
                continue
            self.files.append(m)
            self.states.append(self.state_New)
        return [f for f, s in zip(self.files, self.states) if s==self.state_New]

    def MarkProcessed(self, sources):
        for f in sources:
            try:
                idx = self.files.index(f)
            except ValueError:
                print 'File "%s" not found in WatchSet.' % f
                continue
            self.states[idx] = self.state_Done

class ListState:
    unknown = 0
    open = 1
    closed = 2
    processed = 3

class ArchiveList:
    tstate_Unknown = 0
    tstate_New = 10
    tstate_Done = 20

    def __init__(self, filename, read_now = True):
        self.filename = filename
        self.path = os.path.dirname(filename)
        self.tfiles = []
        self.tstates = []
        self.dest = ""
        self.prefix = ""
        self.state = ListState.unknown
        if read_now:
            self.Read()

    def Read(self):
        self.state = ListState.unknown
        f = open(self.filename)
        lines = f.readlines()
        for l in lines:
            words = l.split()
            if len(words) == 0 or words[0][0] == '#':
                continue
            if l[-1] != '\n':
                break
            if words[0] == "file":
                self.state = ListState.open
                f = words[1]
                if f in self.tfiles:
                    continue
                self.tfiles.append(f)
                self.tstates.append(self.tstate_New)
            elif words[0] == "dest":
                self.dest = words[1]
            elif words[0] == "prefix":
                self.prefix = words[1]
            elif words[0] == "complete":
                self.state = ListState.closed
            elif words[0] == "ack":
                self.state = ListState.processed

    def Mark(self, files, state):
        for f in files:
            try:
                idx = self.tfiles.index(f)
            except ValueError:
                print 'Files "%s" not found in ArchiveList.' % f
                continue
            self.tstates[idx] = state

    def MarkProcessed(self, files=None):
        self.Mark(files, self.tstate_Done)
        if len([0 for s in self.tstates if s!=self.tstate_Done]) == 0:
            self.Close('ack')
        
    def Close(self, message):
        fout = open(self.filename, 'a')
        fout.write('%s\n' % message)
        fout.close()
        self.state = ListState.processed

    def GetReadyFiles(self):
        if self.state == ListState.unknown or self.state == ListState.processed:
            return []
        go_files = [f for f, s, in zip(self.tfiles, self.tstates) if s == self.tstate_New]
        if self.state == ListState.open:
            return go_files[:-1]
        if self.state == ListState.closed:
            return go_files

    def FullPath(self, files=None):
        if files==None:
            files = self.files
        return [ self.path + '/' + f for f in files ]
       

class Rsyncer:
    def __init__(self, dest):
        self.dest = dest

    def Sync(self, sources, suffix):
        full_dest = self.dest + '/' + suffix
        args = ['rsync', '-e', 'ssh -i /home/mce/.ssh/id_rsa', '-uvzr']
        args.extend(sources)
        args.append(full_dest)

        err = os.spawnv(os.P_WAIT, '/usr/bin/rsync', args)
        print 'spawn returned %i' % err
        if (err != 0):
            print 'rsync didn\'t like: ', args
	return err==0
        
class Zipper:
    def __init__(self, remove_source=False):
        self.remove_source = remove_source

    def Compress(self, sources):
        targets = []
        zips = []
	for s in sources:
            z = '%s.gz' % s
            if os.path.lexists(s):
                targets.append(s)
                zips.append(z)
            elif os.path.lexists(z):
                zips.append(z)
        if len(targets) > 0:
            args = ['gzip']
            args.extend(targets)
            err = os.spawnv(os.P_WAIT, '/bin/gzip', args)
            if (err != 0):
                print '%s didn\'t like: ' % args[0], args
                return []
        return zips

def process_options():
    opts = optparse.OptionParser()
    opts.add_option('--pre-scan', '-p')
    opts.add_option('--source-dir', '-s')
    opts.add_option('--dest-location', '-d')
    opts.add_option('--daemon', default=1, type='int')
    opts.add_option('--file-spec', '-f', default="archive_req")
    opts.add_option('--aggression', '-a', default=1)
    opts.add_option('--compress', '-z', default=1)
    opts.add_option('--verbosity', '-v', default=0)
    opts.add_option('--no-pid', action='store_true')

    (op, ar) = opts.parse_args()

    if op.source_dir == None or op.dest_location == None:
        print 'Source directory or destination location not specified!'
        return None

    return op

def keep_alive(cmd, args):
    import subprocess
    while True:
        p = subprocess.Popen([cmd, ] + args)
        p.wait()
        time.sleep(60)

def main():
    op = process_options()

    if op.daemon:
        if op.verbosity > 0:
            print 'Daemonizing.'
        pid = os.fork()
        if pid:
            exit(0)
        if not op.no_pid:
            pidfile = "/var/run/expresspost.pid"
            f = open(pidfile, "w")
            f.write("%i\n" % os.getpid())
            f.close()
            
    # Check for relaunch command
    if len(sys.argv) > 1 and sys.argv[1] == 'KEEP_ALIVE':
        # Remove keep_alive and relaunch
        keep_alive(sys.argv[0], ['--no-pid'] + sys.argv[2:])

    # Copier object, with destination in mind
    r = Rsyncer(op.dest_location)
    zipper = Zipper()
    
    # Prescan actions?
    if op.pre_scan != None:
        if op.verbosity > 0:
            print 'Prescanning.'
        w = WatchSet(op.pre_scan, op.file_spec, recursive=True)
        files = w.Search()
        if op.verbosity > 0:
            print ' %i files found.' % len(files)
        for f in files:
            a = ArchiveList(f)
            if (op.aggression >= 0 and a.state == ListState.closed) or \
                    (op.aggression >=1 and a.state == ListState.open):
                ready_set = a.GetReadyFiles()
                if len(ready_set) > 0:
                    if op.compress:
                        print '  compressing %i files' % len(ready_set)
                        tfiles = zipper.Compress(a.FullPath(ready_set))
                    else:
                        tfiles = a.FullPath(ready_set)
                    print '  rsyncing %i files' % len(tfiles)
                    if r.Sync(tfiles, a.prefix):
                        a.MarkProcessed(ready_set)
            

    if op.verbosity > 0:
        print 'Initializing watcher...'
    w = WatchSet(op.source_dir, op.file_spec, recursive=True)

    # Monitor all archive requests
    count = 0
    archive_set = {}

    update_count = 0
    print 'Looping.'
    while 1:
        count = count + 1

        new_files = w.Search()

	if op.verbosity > 0:
            update_count += 1
            if update_count > 30 or len(new_files) > 0:
                print '%s Managing %i archive sets.  Found %i new files.' % \
                      (time.asctime(), len(archive_set.keys()), len(new_files))
                update_count = 0

        # Add new_files to archive_set
        for f in new_files:
            if not f in archive_set.keys():
                archive_set[f] = ArchiveList(f, read_now=False)
        w.MarkProcessed(new_files)

        # Check all ArchiveLists for changes
        for f in archive_set.keys():
            a = archive_set[f]
            if a.state == ListState.processed:
                archive_set.pop(f)
		continue
            #Update state
            a.Read()

            if (op.aggression >= 0 and a.state == ListState.closed) or \
                    (op.aggression >=1 and a.state == ListState.open):
                ready_set = a.GetReadyFiles()
                if len(ready_set) > 0:
                    if op.compress:
                        print '  compressing %i files' % len(ready_set)
                        tfiles = zipper.Compress(a.FullPath(ready_set))
                    else:
                        tfiles = a.FullPath(ready_set)
                    print '  rsyncing %i files' % len(tfiles)
                    r.Sync(tfiles, a.prefix)
                    a.MarkProcessed(ready_set)

        # Yawn.
        time.sleep(10)

if __name__ == "__main__":
    main()
