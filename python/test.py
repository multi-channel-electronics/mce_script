import auto_setup as ast

# Point to tuning data
source_folder = '/home/data/act/2010/startup/1269227063/'
basename = source_folder.strip('/').split('/')[-1]

ops = ['sa_ramp']

# Group files
tf = ast.util.FileSet(source_folder)

if 'sa_ramp' in ops:
    # Load SA ramp
    ss = [ ast.SARamp(x) for x in tf.stage_all('sa_ramp') ]
    s = ast.SARamp.join(ss, basename)

if 'sq1_ramp' in ops:
    # Load SQ1 ramp
    ss = [ ast.SQ1Ramp(x) for x in tf.stage_all('sq1_ramp_check') ]
    s = ast.SQ1Ramp.join(ss, basename)
    s.reduce()
    s.plot(plot_file='plots/sq1_ramp')
