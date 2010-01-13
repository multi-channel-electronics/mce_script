import subprocess

def register(ctime,type,filename,numpts,note=""):
  return subprocess.call("acq_register " + ctime + " " + type + " " + filename
      + " " + numpts + " \"" + note + "\"")
