from glob import glob
import os

class FileSet(dict):
    def __init__(self, folder):
        self.read(folder)

    def read(self, folder):
        for tag, name in [ \
            ('ssa','sa_ramp'),
            ('sq1servo','sq1_servo'),
            ('sq2servo','sq2_servo'),
            ('sq1ramp','sq1_ramp'),
            ('sq1rampb','tes_ramp'),
            ('sq1rampc','sq1_ramp_check'),
            ]:
            self[name] = {}
            stage_files = glob('%s/*%s' % (folder, tag))
            for f in stage_files:
                for rc in ['RC1', 'RC2', 'RC3', 'RC4', 'RCs', 'RCS']:
                    if rc in f:
                        self[name][rc] = f
                        break
                else:
                    print 'Unmatched tuning file, %s' % f
            
    def stage_all(self, stage):
        return [self[stage][k] for k in sorted(self[stage].keys())] 
