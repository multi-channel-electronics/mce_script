from numpy import *

def load_bias_file(filename):
    data = []
    for line in open(filename, 'r').readlines():
        w = line.split()
        if len(w) == 0 or w[0][0] == '#': continue
        data.append([int(x) for x in w])
    data = array(data)
    n_cols = data.shape[0]/2
    return data[:n_cols,:], data[n_cols:,:]
