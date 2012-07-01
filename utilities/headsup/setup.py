from distutils.core import setup, Extension

from glob import glob
script_files = glob('bin/mhu*')

setup (name = 'mheadsup',
       version = '1.0',
       description = 'Client/server data distributor and plotter.',
       scripts=script_files,
       packages=['mheadsup'])
