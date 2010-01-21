import os, subprocess, time
import auto_setup.config as config
from current_data_name import current_data_name

class tuningData:
    """
    Generic, static data useful to all methods.
    """
    def __init__(self, name=None, exp_file=None, data_root=None):

        # Binary file locations
        self.bin_path = '/usr/mce/bin/'

        # The data root
        if data_root == None:
            data_root = "/data/cryo"
        self.data_root = data_root

        # name
        self.the_time = time.time();
        if name == None:
            name = '%10i' % (self.the_time)
        self.name = name

        # Data directories
        self.current_data = current_data_name(self.data_root)
        self.base_dir = os.path.join(self.data_root, self.current_data)
        self.data_dir = os.path.join(self.base_dir, name)
        self.plot_dir = os.path.join(self.base_dir, 'analysis', name)

        # Various filenames
        self.log_file = os.path.join(self.data_dir, name+'.log')
        self.config_mce_file = os.path.join(self.base_dir,
                "config_mce_auto_setup_" + self.current_data)
        self.note_file = os.path.join(self.data_dir, self.name + "_note")
        self.sqtune_file = os.path.join(self.data_dir, self.name + ".sqtune")
        self.sq2fb_init_file = os.path.join(self.data_dir,
                self.name + ".sq2fb.init")
        self.row_init_file = os.path.join(self.data_dir,
                self.name + ".row.init")

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

    def run(self, args):
        if (not self.openlog_failed and self.log == None):
            try:
                self.log = open(self.log_file, "w+")
            except IOError as (errno, strerror):
                print "Unable to create logfile \"{0}\" (errno: {1}; {2})".\
                        format(self.log_file, errno, strerror)
                print "Logging disabled."
                self.openlog_failed = True

        return subprocess.call([str(x) for x in args], stdout=self.log,
                stderr=self.log)

    def rc_list(self):
        hardware_rc = config.get_exp_param(file, "hardware_rc");
        return [c + 1 for c in range(len(hardware_rc)) if hardware_rc[c] == 1]
    
    def filename(self, rc=None, action=None, ctime=None):
        if ctime == None:
            ctime = time.time()
        s = str(ctime)
        if rc != None:
            s += '_RC%s' % (str(rc))
        if action != None:
            s += '_' + action
        return s
    
    def mce_make_config(self, run_now=False):
        make_command = ["mce_make_config", self.exp_file, self.config_mce_file]
        config_command = self.config_mce_file

        # create the config
        try:
            status = self.run(make_command)
        except OSError, e:
            print "Config creation failed:", e

        if (status > 0):
            return status

        if (run_now):
            try:
                status = self.run(config_command)
            except OSError, e:
                print "Config run failed:", e
  
        return status
