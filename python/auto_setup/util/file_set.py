from __future__ import print_function
from glob import glob
import os

class FileSet(dict):
    """
    Search a tuning folder for tuning data files.
    """

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
            ('sq1ramptes','sq1_ramp_tes'),
            ('rsservo','rs_servo'),
            ('sq1servo_sa','sq1_servo_sa'),
            ]:
            self[name] = {}
            stage_files = glob('%s/*%s' % (folder, tag))
            bias_files = glob('%s/*%s.bias' % (folder, tag))
            # Isolated bias_files should return the basename
            for b in bias_files:
                if b[:-5] not in stage_files:
                    stage_files.append(b[:-5])
            for f in stage_files:
                for rc in ['RC1', 'RC2', 'RC3', 'RC4', 'RCs', 'RCS']:
                    if rc in f:
                        self[name][rc] = f
                        break
                else:
                    print('Unmatched tuning file, %s' % f)
            cfg_file = '%s/experiment.cfg' % folder
            if os.path.exists(cfg_file):
                self['cfg_file'] = cfg_file
                
    def stage_all(self, stage):
        return [self[stage][k] for k in sorted(self[stage].keys())] 
