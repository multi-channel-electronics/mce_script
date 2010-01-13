from os import readlink

def current_data_name(directory="/data/cryo"):
  # This used to involve reading the current_data_name file, but using
  # readlink() is less prone to race conditions

  return readlink(directory + "/current_data")
