from numpy import *

def _load(filename):
    data = []
    for line in open(filename, 'r').readlines():
        w = line.split()
        if len(w) == 0 or w[0][0] == '#' or w[0][0] == '<': continue
        data.append([int(x) for x in w])
    return array(data).transpose()

def load_bias_file(filename):
    """
    Load rows of data from a text file.  Return the first half of the
    columns as one array, and the second half as a second array.
    """
    data = _load(filename)
    n_cols = data.shape[0]/2
    return data[:n_cols,:], data[n_cols:,:]

def load_super_bias_file(filename):
    data = _load(filename)
    n_cols = (data.shape[0]-3)/2
    return data[:3], data[3:n_cols+3,:], data[n_cols+3:,:]
