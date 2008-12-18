#!/usr/bin/python

# Acquire 50 MHz data for various sq2 biases.

from commands import getoutput
from os import system

CFG_FILE='/data/cryo/current_data/experiment.cfg'
CFG_CMD='mas_param -s %s' % CFG_FILE

def config_get(param, type='int'):
    o = getoutput('%s get %s' % (CFG_CMD, param))
    if type == 'int':
        return [int(i) for i in o.split()]
    else:
        return o.split()

def config_set(param, data):
    system('%s set %s %s' %
           (CFG_CMD, param,' '.join([str(d) for d in data])))

def tune():
    system('auto_setup_squids_sh 0 s')

def noise_acq(file_suffix):
    system('mce_raw_acq s 6600 %s' % file_suffix)

def main():

    # Tuning takes 4 minutes, 100 raw acqs takes 1 minute.
    # So this whole thing will take 1hr15
    n_cols = 32
    bias_start = 2500
    bias_step = 2500
    bias_count = 24
    n_fast = 100

    biases = [bias_start + bias_step*i for i in range(bias_count)]
    for bias in biases:
        config_set('default_sq2_bias', [bias]*32)
        tune()
        for j in range(n_fast):
            noise_acq('_bias_%i_%i' % (bias, j))

if __name__ == '__main__':
    main()

