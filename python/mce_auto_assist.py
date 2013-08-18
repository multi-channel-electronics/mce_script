import sys
import os
import time

from auto_setup.util.mas_path import mas_path
mas_path = mas_path()

from ConfigParser import SafeConfigParser

simple_delist = lambda x: x.split()

class DefaultingConfig(SafeConfigParser):
    default_section = 'default'
    active_section = None
    # This actually isn't that much smarter.
    def __init__(self, filename=None):
        SafeConfigParser.__init__(self)
        if filename != None:
            self.read(filename)
    def get_type(self, type_caster, key, default=None):
        for section in [self.active_section, self.default_section]:
            if self.has_section(section) and self.has_option(section, key):
                return type_caster(self.get(section, key))
        if default != None:
            return default
        raise ValueError, 'Unknown config parameter %s:%s' % \
            (section, key)
    def getfloat(self, key, default=None):
        return self.get_type(float, key, default)
    def getint(self, key, default=None):
        return self.get_type(int, key, default)
    def getstr(self, key, default=None):
        return self.get_type(str, key, default)
    def getlist(self, key, default=None):
        return self.get_type(simple_delist, key, default)

class AutoLogger:
    log_file = None
    format_str = '{info} : {script_id} : {msg}'
    start_time = None

    def __init__(self, log_file=None, script_id='<unknown>'):
        if log_file == None:
            log_file = os.path.join(mas_path.data_dir(), 'auto_log.txt')
        self.log_file = log_file
        self.script_id = script_id

    def start_msg(self):
        self.start_time = time.time()
        self.write('%i %s\n' % (self.start_time, time.asctime()), 'START')

    def stop_msg(self):
        self.stop_time = time.time()
        self.write('%i %s - elapsed=%i\n' % \
                       (self.stop_time, time.asctime(),
                        self.stop_time - self.start_time),
                   'STOP')

    def write(self, msg, info='INFO'):
        if self.log_file == None:
            return
        if len(msg) == 0 or msg[-1] != '\n':
            msg = msg + '\n'
        try:
            fout = open(self.log_file, 'a')
        except IOError:
            print 'Failed to open %s, disabling auto-log.' % self.log_file
            self.log_file = None
            return
        kw = {'msg': msg,
              'script_id': self.script_id,
              'info': info}
        fout.write(self.format_str.format(**kw))


if __name__ == '__main__':
    ## test AutoLogger...
    alog = AutoLogger(log_file='test_log.txt', script_id='test_script')
    alog.start_msg()
    alog.write('working...')
    time.sleep(2)
    alog.stop_msg()
