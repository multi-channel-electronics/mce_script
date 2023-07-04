#vim: ts=4 sw=4 et
import os
import subprocess

class mas_path:
    """
    Path look-up made easy.  You can optionally pass the constructor a fibre
    card number and/or mas.cfg path, and/or mas_var path.  If the 'mas_var'
    binary (part of MAS) isn't installed, it will still try to do the Right
    Thing."
    """
    def __init__(self, fibre_card=None, mas_cfg=None, mas_var=None):
        #look for mas_var
        if mas_var:
            self.__mas_var__ = mas_var
        else:
            try: 
                self.__mas_var__ = os.environ["MAS_VAR"]
            except KeyError:
                self.__mas_var__ = "/usr/mce/bin/mas_var"

        # does it exist and is it executable?
        if not (os.path.isfile(self.__mas_var__) and \
                os.access(self.__mas_var__, os.X_OK)):
            self.__mas_var__ = None
        else:
            self.__args__ = [self.__mas_var__]
            if (mas_cfg):
                self.__args__.extend(['-m', mas_cfg])

        # figure out fibre_card
        if (fibre_card):
            self.__fibre_card__ = fibre_card
        else:
            self.__fibre_card__ = int(self.__get_path__("fibre-card",
                "MAS_MCE_DEV", 0))

        if (self.__mas_var__):
            self.__args__.extend(['-n', str(self.__fibre_card__)])

        #cache
        self.__bin_dir__ = None
        self.__config_dir__ = None
        self.__data_dir__ = None
        self.__data_root__ = None
        self.__etc_dir__ = None
        self.__exp_cfg__ = None
        self.__idl_dir__ = None
        self.__mce_cfg__ = None
        self.__mas_prefix__ = None
        self.__mas_root__ = None
        self.__python_dir__ = None
        self.__script_dir__ = None
        self.__temp_dir__ = None
        self.__template_dir__ = None
        self.__test_dir__ = None


    def __get_path__(self, name, env, default):
        # run mas_var, if we have it
        if (self.__mas_var__):
            self.__args__.append('--' + name)
            try:
                proc = subprocess.Popen(self.__args__, stdout = subprocess.PIPE)
                value,stderr = proc.communicate()
                if not proc.returncode:
                    return value.rstrip()
            except OSError:
                pass
            finally:
                self.__args__.pop()

        # check the environment:
        if (env):
            try:
                return os.environ[env]
            except KeyError:
                pass

        # last hurrah: use the default value
        return default
        

    # path functions
    def bin_dir(self):
        if not self.__bin_dir__:
            self.__bin_dir__ = self.__get_path__('bin-dir', 'MAS_BIN',
                    '/usr/mce/bin')
        return self.__bin_dir__

    def config_dir(self):
        if not self.__config_dir__:
            self.__config_dir__ = self.__get_path__('config-dir', 'MAS_CONFIG',
                    '/usr/mce/config')
        return self.__config_dir__

    def data_root(self):
        if not self.__data_root__:
            self.__data_root__ = self.__get_path__('data-root', 'MAS_DATA_ROOT',
                    None)

            # if we have to, determine whether we're running on a multiple card
            # setup
            if self.__data_root__ is None:
                self.__data_root__ = '/data/mce{0}'.format(self.__fibre_card__)
                if not os.path.isdir(self.__data_root__):
                    self.__data_root__ = "/data/cryo"

        return self.__data_root__

    def data_dir(self):
        if not self.__data_dir__:
            self.__data_dir__ = self.__get_path__('data-dir', 'MAS_DATA',
                    os.path.join(self.data_root(), 'current_data'))
        return self.__data_dir__

    def etc_dir(self):
        if not self.__etc_dir__:
            self.__etc_dir__ = self.__get_path__('etc-dir', 'MAS_ETC',
                    '/etc/mce')
        return self.__etc_dir__

    def experiment_file(self):
        if not self.__exp_cfg__:
            self.__exp_cfg__ = self.__get_path__('experiment-file', None, None)
            if self.__exp_cfg__ is None:
                self.__exp_cfg__ = os.path.join(self.data_dir(),
                        "experiment.cfg")
        return self.__exp_cfg__

    def fibre_card(self):
        return self.__fibre_card__

    def hardware_file(self):
        if not self.__mce_cfg__:
            self.__mce_cfg__ = self.__get_path__('hardware-file', None, None)
            if self.__mce_cfg__ is None:
                self.__mce_cfg__ = os.path.join(self.etc_dir(),
                        "mce{0}.cfg".format(self.__fibre_card__))
                if not os.path.isfile(self.__mce_cfg__):
                    self.__mce_cfg__ = os.path.join(self.etc_dir(), "mce.cfg")
        return self.__mce_cfg__

    def idl_dir(self):
        if not self.__idl_dir__:
            self.__idl_dir__ = self.__get_path__('idl-dir', 'MAS_IDL',
                os.path.join(self.mas_root(), "idl_pro"))
        return self.__idl_dir__

    def mas_prefix(self):
        if not self.__mas_prefix__:
            self.__mas_prefix__ = self.__get_path__('prefix', None, '/usr/mce')
        return self.__mas_prefix__

    def mas_root(self):
        if not self.__mas_root__:
            self.__mas_root__ = self.__get_path__('mas-root', 'MAS_ROOT',
                    '/usr/mce/mce_script')
        return self.__mas_root__

    def python_dir(self):
        if not self.__python_dir__:
            self.__python_dir__ = self.__get_path__('python-dir', 'MAS_PYTHON',
                    os.path.join(self.mas_root(), "python"))
        return self.__python_dir__

    def script_dir(self):
        if not self.__script_dir__:
            self.__script_dir = self.__get_path__('script-dir', 'MAS_SCRIPT',
                os.path.join(self.mas_root(), "script"))
        return self.__script_dir

    def temp_dir(self):
        if not self.__temp_dir__:
            self.__temp_dir__ = self.__get_path__('temp-dir', 'MAS_TEMP',
                    "/tmp")
        return self.__temp_dir__

    def template_dir(self):
        if not self.__template_dir__:
            self.__template_dir__ = self.__get_path__('template-dir',
                    'MAS_TEMPLATE', os.path.join(self.mas_root(), "template"))
        return self.__template_dir__

    def test_suite_dir(self):
        if not self.__test_dir__:
            self.__test_dir__ = self.__get_path__('test-suite',
                    'MAS_TEST_SUITE', os.path.join(self.mas_root(),
                    "test_suite"))
        return self.__test_dir__


#test!
if __name__ == '__main__':
    m = mas_path()
    print "Default:"
    print "  Bin Dir   : " + m.bin_dir()
    print "  Config Dir: " + m.config_dir()
    print "  Data Root : " + m.data_root()
    print "  Data Dir  : " + m.data_dir()
    print "  Etc Dir   : " + m.etc_dir()
    print "  Expt. File: " + m.experiment_file()
    print "  Hdwr. File: " + m.hardware_file()
    print "  IDL Dir   : " + m.idl_dir()
    print "  MAS Prefix: " + m.mas_prefix()
    print "  MAS Root  : " + m.mas_root()
    print "  Python Dir: " + m.python_dir()
    print "  Script Dir: " + m.script_dir()
    print "  Temp Dir  : " + m.temp_dir()
    print "  Templ. Dir: " + m.template_dir()
    print "  TSuite Dir: " + m.test_suite_dir()
    print ""
    m = mas_path(mas_var = "/")
    print "Without MAS_VAR:"
    print "  Bin Dir   : " + m.bin_dir()
    print "  Config Dir: " + m.config_dir()
    print "  Data Root : " + m.data_root()
    print "  Data Dir  : " + m.data_dir()
    print "  Etc Dir   : " + m.etc_dir()
    print "  Expt. File: " + m.experiment_file()
    print "  Hdwr. File: " + m.hardware_file()
    print "  IDL Dir   : " + m.idl_dir()
    print "  MAS Prefix: " + m.mas_prefix()
    print "  MAS Root  : " + m.mas_root()
    print "  Python Dir: " + m.python_dir()
    print "  Script Dir: " + m.script_dir()
    print "  Temp Dir  : " + m.temp_dir()
    print "  Templ. Dir: " + m.template_dir()
    print "  TSuite Dir: " + m.test_suite_dir()
