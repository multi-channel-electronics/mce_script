from __future__ import print_function
from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
# vi: ts=4:sw=4:et
import os, subprocess, time
import auto_setup.config as config
from .mas_path import mas_path

class tuningData(object):
    """
    Generic, static data useful to all methods.
    """
    def __init__(self, name=None, exp_file=None, data_dir=None, debug=False,
                 reg_note=None):

        # Path munging object
        self.paths = mas_path();

        # Binary file locations
        self.bin_path = self.paths.bin_dir()
        self.debug = debug

        # The data dir, by default ${MAS_DATA} -- if a data_dir is specified
        # explicitly, the ${MAS_DATA_ROOT}/last_squid_tune symlink isn't updated
        # also, if a data dir is specified, we can't assume it's a directory
        # with a date in it's name, so we just use the current date.
        if data_dir is None:
            data_dir = os.path.realpath(self.paths.data_dir())
            self.no_last_squid_tune = False;
            self.date = os.path.basename(data_dir)
        else:
            self.no_last_squid_tune = True;
            self.date = time.strftime("%Y%m%d")

        # name
        self.the_time = time.time();
        if name is None:
            name = '%10i' % (self.the_time)
        self.name = name

        # canonicalise the data directory
        self.base_dir = os.path.abspath(data_dir)

        # Data directories
        self.data_dir = os.path.join(self.base_dir, name)
        self.plot_dir = os.path.join(self.base_dir, 'analysis', name)

        # Note associated with all acquisitions
        self.reg_note = reg_note

        # Various filenames
        self.log_file = os.path.join(self.data_dir, name+'.log')
        self.config_mce_file = os.path.join(self.base_dir,
                "config_mce_auto_setup_" + self.date)
        self.note_file = os.path.join(self.data_dir, self.name + "_note")
        self.sqtune_file = os.path.join(self.data_dir, self.name + ".sqtune")

        # Experiment configuration
        if exp_file is None:
            exp_file = os.path.join(self.base_dir, 'experiment.cfg')
        self.exp_file = exp_file
        try:
            self.exptfile = config.configFile(exp_file)
        except:
            self.exptfile = config.get_fake_expt(exp_file)

        # Log file
        self.openlog_failed = False
        self.log = None

    def make_dirs(self):
        os.mkdir(self.data_dir)
        os.mkdir(self.plot_dir)

    def get_exp_param(self, key, missing_ok=False, default=None):
        return self.exptfile.get_param(key, missing_ok=missing_ok, default=default)
        #return config.get_exp_param(self.exp_file, key, missing_ok=missing_ok)

    def set_exp_param(self, key, value):
        return self.exptfile.set_param(key, value)
        #return config.set_exp_param(self.exp_file, key, value)

    def set_exp_param_range(self, key, range, value):
        return self.exptfile.set_param(key, value, index=range)
        #return config.set_exp_param_range(self.exp_file, key, range, value)

    def clear_exp_param(self, key):
        return self.set_exp_param(key, 0*self.get_exp_param(key))

    def copy_exp_param(self, src_key, dest_key):
        """
        Copy the value in src_key to dest_key.
        """
        return self.set_exp_param(dest_key, self.get_exp_param(src_key))

    def run(self, args, no_log=False):
        if (no_log):
            log = None
        else:
            if (not self.openlog_failed and self.log is None):
                try:
                    self.log = open(self.log_file, "w+")
                    self.log.write("Auto tuning run started "
                        + time.asctime(time.gmtime(self.the_time)) + " UTC\n")
                    self.log.write("Dir:  " + self.base_dir + "\n")
                    self.log.write("Name: " + self.name + "\n")
                except IOError as xxx_todo_changeme:
                    (errno, strerror) = xxx_todo_changeme.args
                    print("Unable to create logfile \"{0}\" (errno: {1}; {2})".\
                            format(self.log_file, errno, strerror))
                    print("Logging disabled.")
                    self.openlog_failed = True
            log = self.log

        if (log):
          log.write("\nExecuting")
          log.writelines([" " + str(x) for x in args] + ["\n"])
          log.flush()

        if (self.debug):
          print("Executing: " + str(args))

        s = subprocess.call([str(x) for x in args], stdout=log, stderr=log)

        if (log):
          log.write("Exit Status: " + str(s) + "\n")
          log.flush()
        return s

    def rc_list(self):
        # Since the all-card tuning relies on RCS data acquisition, get the RC list
        # from hardware_rc_data, which determines RCS acq membership.
        #hardware_rc = config.get_exp_param(self.exp_file, "hardware_rc_data");
        hardware_rc = self.exptfile.get_param("hardware_rc_data")
        return [c + 1 for c in range(len(hardware_rc)) if hardware_rc[c] == 1]

    def column_list(self):
        cols = []
        for i in self.rc_list():
            cols += [x+(i-1)*8 for x in range(8)]
        return cols

    def filename(self, rc=None, action=None, ctime=None, absolute=False):
        if ctime is None:
            ctime = time.time()
        acq_id = str(int(ctime))
        s = acq_id
        if rc is not None:
            s += '_RC%s' % (str(rc))
        if action is not None:
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
        except OSError as e:
            print("Config creation failed:", e)
            return -1

        if (status > 0):
          raise ValueError("mce_make_config failed.")

        # run it
        if (run_now):
            try:
                status = self.run([self.config_mce_file])
            except OSError as e:
                print("Config run failed:", e)
                return -1
  
        if (status > 0):
          raise ValueError("Executing " + self.config_mce_file + " failed.")

        return 0

    def writelog(self, message, flush=False):
        if (self.log):
            self.log.write(message)
            if (flush):
                self.log.flush()

    def write_sqtune(self, filename=None, sq_data=None,
                     append=True, rcs=None, block=None):
        def compose_col_row(label, data, format='%f'):
            s = ''
            for i, d in enumerate(data):
                s += '<%s> ' % (label % i)
                s += ' '.join([format % r for r in d]) + '\n'
            return s
        def compose_vector(label, data, format='%f'):
            s = '<%s> ' % (label)
            s += ' '.join([format %r for r in data]) + '\n'
            return s

        if filename is None:
            filename = self.sqtune_file
        if sq_data is None:
            # Basic info
            if block is None:
                block = 'SQUID_INIT'
            is_mux11d = self.get_exp_param('hardware_mux11d', 0) == 1
            data = \
                '<SQ_tuning_date> %s\n' % self.date + \
                '<SQ_tuning_dir> %s\n' % self.name + \
                '<SQ_tuning_hardware> %s\n' % {False: 'classic',
                                               True:  'mux11d'}[is_mux11d]
            if rcs is not None:
                if rcs[0] == 's':
                    rcs = self.rc_list()
                cols = []
                for r in rcs:
                    cols = cols + [(r-1)*8+c for c in range(8)]
                data = data + \
                    '<SQ_RCs> %s\n' % ' '.join(['%i' % x for x in rcs]) + \
                    '<SQ_columns> %s\n' % ' '.join(['%i' % x for x in cols])
            # Package...
            data = [{'style': 'raw', 'data': data}]
        if sq_data is not None:
            sq_data = sq_data.sqtune_report()
            if block is None:
                block = sq_data['block']
            data = sq_data['data']
        f = open(filename, 'a' if append else 'w')
        f.write("<%s>\n" % block)
        for item in data:
            s, fmt = item.get('style', 'vector'), item.get('format', '%i')
            if s == 'vector':
                f.write(compose_vector(item['label'], item['data'], format=fmt))
            elif s == 'col_row':
                f.write(compose_col_row(item['label'], item['data'], format=fmt))
            elif s == 'raw':
                f.write(item['data'])
            else:
                raise RuntimeError('unknown item style "%s"' % s)
        f.write("</%s>\n" % block)
        f.close()
        
        #this isn't updated if the user specified a data_dir when initialising
        #the tuning
        if  self.no_last_squid_tune != True:
            lst = os.path.join(self.paths.data_root(), "last_squid_tune")
            if os.path.lexists(lst):
                os.remove(lst)
            os.symlink(filename, lst)

    def write_note(self, note, filename=None):
        if filename is None:
            filename = self.note_file
        f = open(filename, "w+")
        f.write("#Note entered with SQUID autotuning data acquisition\n")
        f.write(note)
        f.write("\n")
        f.close()

    def cmd(self, command):
        return self.run(["mce_cmd", "-q", "-x"] + command.split())

    def register(self, ctime, type, filename, numpts, note=None):
        if note is None:
            note = self.reg_note
        if note is None:
            note = ''
        cmd = ["mce_acq_register", ctime, type, filename, numpts, note]

        return self.run(cmd)

    def register_plots(self, *args, **kwargs):
        if kwargs.get('init', False):
            from .plot_reg import plot_registrar
            self.plot_reg = plot_registrar(self.base_dir+'/analysis', self.name)
        if self.plot_reg is None:
            return
        for a in args:
            self.plot_reg.add(os.path.split(a)[1])
