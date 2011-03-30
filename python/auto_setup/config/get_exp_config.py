import numpy
import subprocess

# this implementation is kind of lame...
string_keys = ['array_id', 'dead_mask_list', 'frail_mask_list']
float_keys = ['sa_offset_bias_ratio', 'sq2_servo_gain', 'sq1_servo_gain',
        'tes_bias_normal_time']
int_keys = ['array_width', 'hardware_rc', 'hardware_sync',
        'hardware_bac', 'hardware_rect', 'hardware_rc_data', 'sb0_select_clk',
        'sb0_use_dv', 'sb0_use_sync', 'sb1_select_clk', 'sb1_use_dv',
        'sb1_use_sync', 'default_num_rows', 'default_sample_num',
        'default_data_mode', 'default_flux_jumping', 'default_servo_p',
        'default_servo_i', 'default_servo_d', 'default_sa_bias',
        'default_sq2_bias', 'default_sq1_bias', 'default_sq1_bias_off',
        'columns_off', 'stop_after_sq1_servo', 'sa_flux_quanta', 'sa_ramp_bias',
        'sa_ramp_flux_start', 'sa_ramp_flux_count', 'sa_ramp_flux_step',
        'sa_ramp_bias_start', 'sa_ramp_bias_step', 'sa_ramp_bias_count',
        'sq2_flux_quanta',
        'sq2_rows', 'sq2_servo_flux_start', 'sq2_servo_flux_count',
        'sq2_servo_flux_step', 'sq1_servo_flux_start', 'sq1_servo_flux_count',
        'sq1_servo_flux_step', 'sq2_servo_bias_ramp', 'sq2_servo_bias_start',
        'sq2_servo_bias_count', 'sq2_servo_bias_step', 'sq1_servo_all_rows',
        'sq1ramp_plot_rows', 'locktest_plot_row', 'sq1_ramp_flux_start',
        'sq1_ramp_flux_step', 'sq1_ramp_flux_count', 'locktest_pass_amplitude',
        'sq1servo_slope', 'sq2servo_slope', 'sq1_ramp_tes_bias',
        'sq1_ramp_tes_bias_start', 'sq1_ramp_tes_bias_step',
        'sq1_ramp_tes_bias_count', 'tes_bias_idle', 'tes_bias_normal',
        'tes_bias_do_reconfig', 'sq2servo_safb_init',
        'sq1servo_sq2fb_init', 'ramp_tes_start', 'ramp_tes_step',
        'ramp_tes_count', 'ramp_tes_final_bias', 'ramp_tes_initial_pause',
        'ramp_tes_period_us', 'iv_data_mode', 'bias_line_card',
        'bias_line_para', 'config_rc', 'config_sync', 'config_fast_sq2',
        'config_dead_tes', 'config_frail_tes', 'data_rate', 'row_len',
        'num_rows', 'num_rows_reported', 'readout_row_index', 'sample_dly',
        'sample_num', 'fb_dly', 'row_dly', 'data_mode', 'flux_jumping',
        'servo_mode', 'servo_p', 'servo_i', 'servo_d', 'dead_detectors',
        'tes_bias', 'row_order', 'config_flux_quanta_all', 'flux_quanta',
        'flux_quanta_all', 'fb_const', 'sq1_bias', 'sq1_bias_off', 'sq2_bias',
        'sq2_fb', 'sq2_fb_set', 'sa_bias', 'sa_fb', 'sa_offset',
        'config_adc_offset_all', 'adc_offset_c', 'adc_offset_cr',
        'frail_servo_p', 'frail_servo_d', 'frail_servo_i', 'frail_detectors'] 

def mas_param(file, key, type, raw=False):
    try:
        p = subprocess.Popen(["mas_param", "-s", file, "get", key],
                stdout=subprocess.PIPE);
        value = p.communicate()[0];
        status = p.wait();
    except OSError, (errno, strerror):
        print "Failed to load parameter " + key + \
            "\n[Errno {0}] {1}".format(errno, strerror)
        return None

    if (status):
        return None

    if raw:
        return value.strip()

    if (type == 0): # scalar or vector int
        v = value.split()
        if (len(v) == 1):
            return int(v[0])
        else:
            return numpy.array([int(x) for x in v])
    elif (type == 1): # scalar or vector float
        v = value.split()
        if (len(v) == 1):
            return float(v[0])
        else:
            return numpy.array([float(x) for x in v])
    else: # scalar or vector string
        v = value.split()
        if (len(v) == 1):
            #Remove white space and lead/trail quotes.
            return value.strip()[1:-1]
        else:
            return [s.strip()[1:-1] for s in v]

def set_exp_param(file, key, value):
    """Writes the value given to the specified parameter of the experimental
    configuration."""

    if (key == "_source"):
        return None;

    command = ["mas_param", "-s", file, "set", key]

    try:
        iter(value)
    except TypeError:
        value = [value]

    command += [str(x) for x in value]
    status = subprocess.call(command)

    if (status != 0):
        raise OSError("An error occurred while setting " + key)

def get_exp_param(file, key, array=True, missing_ok=False):
    """Returns the value of one parameter of the experimental configuration.

    file: the name of the configuration file to read.
    key: the name of the parameter to read."""

    if (key == "_source"):
        # for compatibility with the dictionary
        return file;
    if key in string_keys:
        v = mas_param(file, key, 2)
    elif key in float_keys:
        v = numpy.array(mas_param(file, key, 1))
    elif key in int_keys:
        v = numpy.array(mas_param(file, key, 0))
    else:
        raise KeyError("unknown experimental parameter: " + key)
    
    if (not missing_ok and v == None):
        raise KeyError("key [ " + key + " ] missing from " + file)

    return v

def get_exp_config(file):
    """Returns a dictionary containing the experimental configuration.

    file: the name of the configuration file to read."""

    config = {'_source': file};

    for key in (string_keys):
        config[key] = mas_param(file, key, 2)

    for key in (float_keys):
        config[key] = numpy.array(mas_param(file, key, 1))

    for key in (int_keys):
        config[key] = numpy.array(mas_param(file, key, 0))

    return config;

def set_exp_param_range(file, key, range, value):
    a = get_exp_param(file, key)
    a[range] = value
    set_exp_param(file, key, a)


#
# Dynamic system -- determine cfg file parameters and types at
#  runtime.
#

def get_param_descriptions(file):
    """
    Parse the configuration file description obtained from 'mas_param
    info'.  Return a list of parameter names (in order encountered),
    and a dictionary mapping the names to a property description.
    """
    try:
        p = subprocess.Popen(["mas_param", "-s", file, "info"],
                stdout=subprocess.PIPE);
        value = p.communicate()[0]
        status = p.wait();
    except OSError, (errno, strerror):
        print "Failed to get parameter info table from mas_param\n" \
            "[Errno {0}] {1}".format(errno, strerror)
        return None
    params = []
    info = {}
    for line in value.split('\n'):
        w = map(str.strip, line.split(':'))
        if len(w) == 0 or len(w[0]) == 0 or w[0][0] == '#':
            continue
        if len(w) != 4:
            raise RuntimeError, "Failed to parse mas_param info line %s" % line
        name, dtype, arrayness, size = w[0], w[1], w[2]=='array', int(w[3])
        params.append(name)
        info[name] = {'type': dtype,
                      'is_array': arrayness,
                      'length': size}
    return params, info

class exptFile:
    casts = {'integer': int,
             'float': float,
             'string': lambda x: str(x[1:-1])}

    def __init__(self, filename=None, read=True):
        self.data = {}
        self.filename = filename
        if self.filename != None:
            self.read(refresh_info=True)

    def read_param(self, name):
        val = mas_param(self.filename, name, 0, raw=True)
        desc = self.info[name]
        cast = self.casts[desc['type']]
        if desc['is_array']:
            val = numpy.array(map(cast, val.split()))
        else:
            val = cast(val)
        self.data[name] = val
        return val

    def read(self, refresh_info=False):
        if refresh_info:
            self.names, self.info = get_param_descriptions(self.filename)
        self.data = {}
        for n in self.names:
            self.read_param(n)

    def get_param(self, name, missing_ok=False):
        if missing_ok and not name in self.data:
            return None
        return self.data[name]
    
    def set_param(self, name, data, index=None):
        if index == None:
            self.data[name] = data
        else:
            self.data[name][index] = data
        set_exp_param(self.filename, name, data)

    def write(self):
        for k, v in iter(self.data):
            self.write_param(k,v)


if __name__ == '__main__':
    # Unit test...
    fn = '/data/cryo/current_data/experiment.cfg'
    cfg = exptFile(fn)
    print cfg.get_param('dead_mask_list')
