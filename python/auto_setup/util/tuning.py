import os, subprocess
import auto_setup.config as config
from current_data_name import current_data_name

class tuningData:
    """
    Generic, static data useful to all methods.
    """
    def __init__(self, name=None, exp_file=None):
        if name == None:
            the_time = time.time();
            name = '%10i' % (the_time)
        self.name = name
        self.base_dir = current_data_name()
        self.data_dir = os.path.join(self.base_dir, name)
        self.plot_dir = os.path.join(self.base_dir, 'analysis', name)

        # Binary file locations
        self.bin_path = '/usr/mce/bin/'

        # Experiment configuration
        if exp_file == None:
            exp_file = os.path.join(self.base_dir, 'experiment.cfg')
        self.exp_file = exp_file

        # Log file
        self.log_file = os.path.join(self.data_dir, name+'.log')

    def make_dirs(self):
        os.mkdir(self.data_dir)
        os.mkdir(self.plot_dir)

    def get_exp_param(self, key):
        return config.get_exp_config(self.exp_file, key)

    def run(self, args):
        return subprocess.call([str(x) for x in args])
    
    def filename(self, rc=None, action=None, ctime=None):
        if ctime == None:
            ctime = time.time()
        s = str(ctime)
        if rc != None:
            s += '_RC%s' % (str(rc))
        if action != None:
            s += '_' + action
        return s

