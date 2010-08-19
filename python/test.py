import auto_setup as ast
ast.util.interactive_errors()

# Point to tuning data
source_folder = '/home/data/act/2010/startup/1269227063/'
basename = source_folder.strip('/').split('/')[-1]

ops = ['sq1_servo']

# Group files
tf = ast.util.FileSet(source_folder)

if 'sa_ramp' in ops:
    # Load SA ramp
    ss = [ ast.SARamp(x) for x in tf.stage_all('sa_ramp') ]
    s = ast.SARamp.join(ss)
    s.reduce1()
    s2 = s.subselect()
    s2.reduce(slope=1.)
    s2.plot(plot_file='plots/sa_ramp')

if 'sq2_servo' in ops:
    ss = [ ast.SQ2Servo(x) for x in tf.stage_all('sq2_servo') ]
    s = ast.SQ2Servo.join(ss).split()[0]
    s.reduce(slope=1.)
    s.plot(plot_file='plots/sq2_servo')

if 'sq1_servo' in ops:
    ss = [ ast.SQ1Servo(x) for x in tf.stage_all('sq1_servo') ]
    s = ast.SQ1Servo.join(ss).split()[0]
    s.reduce(slope=1.)
    s.plot(plot_file='plots/sq1_servo')

if 'sq1_ramp' in ops:
    # Load SQ1 ramp
    ss = [ ast.SQ1Ramp(x) for x in tf.stage_all('sq1_ramp_check') ]
#    s1 = ast.SQ1Ramp.join(ss, basename)
    s = ast.SQ1Ramp.join2(ss)
    s.reduce()
    s.plot(plot_file='plots/sq1_ramp')
