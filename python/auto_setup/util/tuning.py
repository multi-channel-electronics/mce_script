import os, subprocess
import auto_setup.config as config
from current_data_name import current_data_name

class tuningData:
    """
    Generic, static data useful to all methods.
    """
    def __init__(self, name=None, exp_file=None, data_root=None):

        # The data root
        if data_root == None:
            try:
                data_root = os.environ["MAS_DATA"];
            except KeyError:
                data_root = "/data/cryo"
        self.data_root = data_root

        # name
        if name == None:
            the_time = time.time();
            name = '%10i' % (the_time)
        self.name = name

        # Data directories
        self.base_dir = current_data_name(self.data_root)
        self.data_dir = os.path.join(self.base_dir, name)
        self.plot_dir = os.path.join(self.base_dir, 'analysis', name)
        self.config_mce_file = os.path.join(self.base_dir,
                "config_mce_auto_setup_" + self.base_dir)

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
        return config.get_exp_param(self.exp_file, key)

    def set_exp_param(self, key, value):
        return config.set_exp_param(self.exp_file, key, value)

    def set_exp_param_range(self, key, range, value):
        return config.set_exp_param_range(self.exp_file, key, range, value)

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
