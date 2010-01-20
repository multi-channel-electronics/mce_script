import subprocess

def cmd(command):
    return subprocess.call("mce_cmd -q -x " + command)
