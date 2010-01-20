import subprocess

def mce_make_config(params_file=None, filename=None, run_now=None):

    make_command = ["mce_make_config"]
    config_command = filename

    if (params_file != None):
        make_command.append(params_file)
        if (filename != None):
            make_command.append(filename)
  
    # create the config
    try:
        status = subprocess.call(make_command)
    except OSError, e:
        print "Config creation failed:", e

    if (status > 0):
        return status

    if (run_now):
        try:
            status = subprocess.call(config_command)
        except OSError, e:
            print "Config run failed:", e
  
    return status
