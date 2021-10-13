from __future__ import print_function
from builtins import object
#!/usr/bin/python

import os, time
from glob import glob
import stat
import optparse

class WatchSet(object):
    """Track a set of files matching a certain pattern."""

    def __init__(self, base_dir, pattern, recursive = False,
                 match_dirs = True, match_files = True):
        self.base_dir = base_dir
        self.pattern = pattern
        self.recursive = recursive
        self.match_dirs = match_dirs
        self.match_files = match_files
        self.processed = set()

    def SearchCallback(self, arg, dir, files):
        for f in files:
            if f == self.pattern:
                ff = dir + '/' + f
                s = os.stat(ff)
                d = stat.S_ISDIR(s[stat.ST_MODE])
                if (d and self.match_dirs) or (not d and self.match_files):
                    self.matches = self.matches.union([dir + '/' + f])

    def Search(self, new_only = False):
        self.matches = set()
        if (self.recursive):
            os.path.walk(self.base_dir, self.SearchCallback, 0)
        else:
            matches = glob(self.base_dir + '/' + self.pattern)
            for m in matches:
                s = os.stat(m)
                d = stat.S_ISDIR(s[stat.ST_MODE])
                if (d and not self.match_dirs) or (not d and not self.match_files):
                    matches.remove(m)
            self.matches = set(matches)

        if new_only:
            return FindNew(self.matches)
        return set(self.matches)

    def FindNew(self, sources):
        new_sources = set(sources) - self.processed
        return new_sources

    def MarkProcessed(self, sources):
        self.processed = self.processed.union(sources)

class ListState(object):
    unknown = 0
    open = 1
    closed = 2
    processed = 3

class ArchiveList(object):
    def __init__(self, filename, read_now = True):
        self.filename = filename
        self.path = os.path.dirname(filename)
        self.files = []
        self.files_done = set()
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
            if words == []:
                continue
            if words[0] == "file":
                self.state = ListState.open
                self.files.append(words[1])
            elif words[0] == "dest":
                self.dest = words[1]
            elif words[0] == "prefix":
                self.prefix = words[1]
            elif words[0] == "complete":
                self.state = ListState.closed
            elif words[0] == "ack":
                self.state = ListState.processed

    def MarkProcessed(self, files=None):
        if files is None:
            files = self.files
        self.files_done = self.files_done.union(set(files))
        if set(self.files).difference(set(self.files_done)) == set() and \
                self.state == ListState.closed:
            f = open(self.filename, "a")
            f.write("ack\n")
            f.close()
            self.state = ListState.processed

    def GetReadyFiles(self):
        if self.state == ListState.unknown or self.state == ListState.processed:
            return set()
        elif self.state == ListState.open:
            return set(self.files[:-1]).difference(self.files_done)
        elif self.state == ListState.closed:
            return set(self.files).difference(self.files_done)

    def FullPath(self, files=None):
        if files is None:
            files = self.files
        return [ self.path + '/' + f for f in files ]
       

class Rsyncer(object):
    def __init__(self, dest, key=None):
        self.dest = dest
        self.key = key

    def Sync(self, sources, suffix, extra_permissions=None):
        full_dest = self.dest + '/' + suffix
        args = ['rsync', '-e', 'ssh -i %s'%self.key, '-uvzr']
        args.extend(sources)
        args.append(full_dest)

        err = os.spawnv(os.P_WAIT, '/usr/bin/rsync', args)
        if (err != 0):
            print('rsync didn\'t like: ', args)
            return

        # split dest into host and folder...
        if extra_permissions is not None:
            host, folder = full_dest.split(':')
            argstr = 'ssh -i %s %s chmod %s %s' % \
                (self.key, host, extra_permissions, folder)
            err = os.spawnv(os.P_WAIT, '/usr/bin/ssh', argstr.split())
            if (err != 0):
                print('ssh didn\'t like: ', argstr)
        

def process_options():
    opts = optparse.OptionParser()
    opts.add_option('--source-dir', '-s')
    opts.add_option('--dest-location', '-d')
    opts.add_option('--daemon', default=1, type='int')
    opts.add_option('--file-spec', '-f', default="archive_req")
    opts.add_option('--aggression', '-a', type='int', default=1)
    opts.add_option('--compress', '-z', default=1)
    opts.add_option('--ssh-key', '-k')

    (op, ar) = opts.parse_args()

    if op.source_dir is None or op.dest_location is None:
        print('Source directory or destination location not specified!')
        return None

    return op

def main():

    op = process_options()

    # Copier object, with destination in mind
    r = Rsyncer(op.dest_location, op.ssh_key)
    
    # Watch for changes in the archive files.
    w = WatchSet(op.source_dir, op.file_spec, recursive=True)

    if op.daemon:
        pid = os.fork()
        if pid:
            exit(0)
        pidfile = "/var/run/expresspost.pid"
        f = open(pidfile, "w")
        f.write("%i\n" % os.getpid())
        f.close()
            
    # Monitor all archive requests
    count = 0
    archive_set = set()
    while 1:
        w.Search()

        count = count + 1
        
        # Get list of archive files to process
        search_results = w.matches
        
        # Restrict to files we don't already know about
        new_matches = set(w.matches).difference( set( [a.filename for a in archive_set] ) )

        # Re-load existing archive lists
        for a in archive_set:
            if a.state <= ListState.open:
                a.Read()

        # Add new lists
        archive_set = archive_set.union(set([ ArchiveList(m) for m in new_matches ]))

#        print count
#        print new_matches
#        print [ (a.filename,a.state) for a in archive_set if a.state != ListState.processed ]

        for a in archive_set:
            # Depending on aggression level, process some files.

            #Least aggressive; wait for list to be complete
            if (op.aggression >= 0 and a.state == ListState.closed) or \
                    (op.aggression >=1 and a.state == ListState.open):
                ready_set = a.GetReadyFiles()
                if ready_set != set():
                    r.Sync(a.FullPath(ready_set), a.prefix, extra_permissions='g+w')
                    a.MarkProcessed(ready_set)

        # Yawn.
        time.sleep(10)

if __name__ == "__main__":
    main()
