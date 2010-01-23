# vi: ts=4:sw=4:et
import os, subprocess, time
import auto_setup.config as config

class tuningData:
    """
    Generic, static data useful to all methods.
    """
    def __init__(self, name=None, exp_file=None, data_root=None, debug=False):

        # Binary file locations
        self.bin_path = '/usr/mce/bin/'
        self.debug = debug

        # The data root
        if data_root == None:
            data_root = "/data/cryo"
        self.data_root = data_root

        # name
        self.the_time = time.time();
        if name == None:
            name = '%10i' % (self.the_time)
        self.name = name

        # current data directory -- we get this from the "current_data" symlink,
        # which may or may not point to an absolute path
        self.current_data = os.path.basename(
                os.readlink(os.path.join(self.data_root, "current_data")))

        # Data directories
        self.base_dir = os.path.join(self.data_root, self.current_data)
        self.data_dir = os.path.join(self.base_dir, name)
        self.plot_dir = os.path.join(self.base_dir, 'analysis', name)

        # Various filenames
        self.log_file = "log.file"#os.path.join(self.data_dir, name+'.log')
        self.config_mce_file = os.path.join(self.base_dir,
                "config_mce_auto_setup_" + self.current_data)
        self.note_file = os.path.join(self.data_dir, self.name + "_note")
        self.sqtune_file = os.path.join(self.data_dir, self.name + ".sqtune")

        # Experiment configuration
        if exp_file == None:
            exp_file = os.path.join(self.base_dir, 'experiment.cfg')
        self.exp_file = exp_file

        # Log file
        self.openlog_failed = False
        self.log = None

    def make_dirs(self):
        os.mkdir(self.data_dir)
        os.mkdir(self.plot_dir)

    def get_exp_param(self, key):
        return config.get_exp_param(self.exp_file, key)

    def set_exp_param(self, key, value):
        return config.set_exp_param(self.exp_file, key, value)

    def set_exp_param_range(self, key, range, value):
        return config.set_exp_param_range(self.exp_file, key, range, value)

    def run(self, args, no_log=False):
        if (no_log):
            log = None
        else:
            if (not self.openlog_failed and self.log == None):
                try:
                    self.log = open(self.log_file, "w+")
                    self.log.write("Auto tuning run started "
                        + time.asctime(time.gmtime(self.the_time)) + " UTC\n")
                    self.log.write("Dir:  " + self.base_dir + "\n")
                    self.log.write("Name: " + self.name + "\n")
                except IOError, (errno, strerror):
                    print "Unable to create logfile \"{0}\" (errno: {1}; {2})".\
                            format(self.log_file, errno, strerror)
                    print "Logging disabled."
                    self.openlog_failed = True
            log = self.log

        if (log):
          log.write("\nExecuting")
          log.writelines([" " + str(x) for x in args] + ["\n"])
          log.flush()

        if (self.debug):
          print "Executing: " + str(args)

        s = subprocess.call([str(x) for x in args], stdout=log, stderr=log)

        if (log):
          log.write("Exit Status: " + str(s) + "\n")

    def rc_list(self):
        hardware_rc = config.get_exp_param(self.exp_file, "hardware_rc");
        return [c + 1 for c in range(len(hardware_rc)) if hardware_rc[c] == 1]
    
    def filename(self, rc=None, action=None, ctime=None, absolute=False):
        if ctime == None:
            ctime = time.time()
        acq_id = str(ctime)
        s = acq_id
        if rc != None:
            s += '_RC%s' % (str(rc))
        if action != None:
            s += '_' + action

        if (absolute):
            s = os.path.join(self.data_dir, s)
        else:
            s = os.path.join(self.name, s)

        return s, acq_id
    
    def write_config(self, run_now=True):
        # create the config
        try:
            status = self.run(["mce_make_config", self.exp_file,
              self.config_mce_file])
        except OSError, e:
            print "Config creation failed:", e
            return -1

        if (status > 0):
          raise ValueError("mce_make_config failed.")

        # run it
        if (run_now):
            try:
                status = self.run([self.config_mce_file])
            except OSError, e:
                print "Config run failed:", e
                return -1
  
        if (status > 0):
          raise ValueError("Executing " + self.config_mce_file + "failed.")

        return 0

    def writelog(self, message, flush=False):
        if (self.log):
            self.log.write(message)
            if (flush):
                self.log.flush()

    def cmd(self, command):
        return self.run(["mce_cmd", "-q", "-x"] + command.split())

    def register(self, ctime, type, filename, numpts, note=None):
        cmd = ["acq_register", ctime, type, filename, numpts]
        if (note):
            cmd.append(note)
        else:
            cmd.append("")

        return self.run(cmd)