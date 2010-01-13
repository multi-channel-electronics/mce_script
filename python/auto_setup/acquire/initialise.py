import subprocess

def initialise(rc, check_bias=False, log=None):
  # check whether the SSA and SQ2 biases have already been set
  on_bias = False
  if (check_bias):
    for (c in rc):
      exit = subprocess.Popen(["check_zero", "rc" + c, "sa_bias"], stdout=log,
          stderr=log).wait()
