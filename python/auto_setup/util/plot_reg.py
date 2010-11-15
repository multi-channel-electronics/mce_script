import os

class plot_registrar:
    def __init__(self, root, child):
        self.filename = os.path.join(root, child, 'mceplots_archive')
        fout = open(self.filename, 'w')
        fout.write('prefix %s/\n' % child)
        fout.close()

    def _write(self, line):
        fout = open(self.filename, 'a')
        fout.write('%s\n' % line)
        fout.close()
        
    def add(self, file):
        self._write('file %s' % file)

    def __del__(self):
        self._write('complete')

