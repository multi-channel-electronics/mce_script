# vi: ts=4:sw=4:et
import os, subprocess, time
import auto_setup.config as config

class tuningData:
    """
    Generic, static data useful to all methods.
    """
    def __init__(self, name=None, exp_file=None, data_root=None, debug=False,
                 reg_note=None):

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
        self.current_data = os.path.join(self.data_root, "current_data")
        if os.path.exists(self.current_data):
            self.current_data = os.path.basename(os.readlink(self.current_data))

        # Data directories
        self.base_dir = os.path.join(self.data_root, self.current_data)
        self.data_dir = os.path.join(self.base_dir, name)
        self.plot_dir = os.path.join(self.base_dir, 'analysis', name)

        # Note associated with all acquisitions
        self.reg_note = reg_note

        # Various filenames
        self.log_file = os.path.join(self.data_dir, name+'.log')
        self.config_mce_file = os.path.join(self.base_dir,
                "config_mce_auto_setup_" + self.current_data)
        self.note_file = os.path.join(self.data_dir, self.name + "_note")
        self.sqtune_file = os.path.join(self.data_dir, self.name + ".sqtune")

        # Experiment configuration
        if exp_file == None:
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

    def get_exp_param(self, key, missing_ok=False):
        return self.exptfile.get_param(key, missing_ok=missing_ok)
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
        if ctime == None:
            ctime = time.time()
        acq_id = str(int(ctime))
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
          raise ValueError("Executing " + self.config_mce_file + " failed.")

        return 0

    def writelog(self, message, flush=False):
        if (self.log):
            self.log.write(message)
            if (flush):
                self.log.flush()

    def write_sqtune(self, filename=None, sq1_ramp=None, link=False):
        def compose_col_row(label, data, format='%f'):
            s = ''
            for i, d in enumerate(data):
                s += '<%s> ' % (label % i)
                s += ' '.join([format % r for r in d]) + '\n'
            return s

        if filename == None:
            filename = self.sqtune_file
        done = sq1_ramp != None
        f = open(filename, 'w')
        f.write("<SQUID>\n")
        f.write("<SQ_tuning_completed> %i\n" % int(done))
        f.write("<SQ_tuning_date> %s\n" % self.current_data)
        f.write("<SQ_tuning_dir> %s\n" % self.name)
        if sq1_ramp != None:
            for item in sq1_ramp.sqtune_report():
                s = item['style']
                if s == 'col_row':
                    f.write(compose_col_row(item['label'], item['data'],
                                            format=item['format']))
                else:
                    raise RuntimeError, 'unknown item style "%s"' % s
        f.write("</SQUID>\n")
        f.close()
        
        lst = os.path.join(self.data_root, "last_squid_tune")
        if os.path.lexists(lst):
            os.remove(lst)
        os.symlink(filename, lst)

    def write_note(self, note, filename=None):
        if filename == None:
            filename = self.note_file
        f = open(filename, "w+")
        f.write("#Note entered with SQUID autotuning data acquisition\n")
        f.write(note)
        f.write("\n")
        f.close()

    def cmd(self, command):
        return self.run(["mce_cmd", "-q", "-x"] + command.split())

    def register(self, ctime, type, filename, numpts, note=None):
        if note == None:
            note = self.reg_note
        if note == None:
            note = ''
        cmd = ["acq_register", ctime, type, filename, numpts, note]
        return self.run(cmd)

    def register_plots(self, *args, **kwargs):
        if kwargs.get('init', False):
            from plot_reg import plot_registrar
            self.plot_reg = plot_registrar(self.base_dir+'/analysis', self.name)
        if self.plot_reg == None:
            return
        for a in args:
            self.plot_reg.add(os.path.split(a)[1])
