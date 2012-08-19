from nets import *
import util

import numpy

class dataClient:
    ctype = None
    name = None
    connected = False
    controls = {}
    data = []
    def __init__(self, addr=None, name=None):
        self.connected = False
        if name != None:
            self.name = name
        if addr != None:
            self.connect(addr)
    def __repr__(self):
        constr = 'connected'
        if not self.connected:
            constr = 'not '+constr
        return '<%s (%s); %s; %s>' % (self.__class__.__name__, self.name,
                                      constr, str(self.addr))
    def connect(self, addr=None):
        if addr != None:
            self.addr = addr
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect(decode_address(self.addr))
        except socket.error as err:
            print 'Failed to connect to server; error %i (%s)' % \
                (err.args[0], err.args[1])
            return False
        try:
            self.sock.settimeout(0.1)
            if self.name != None:
                self.set_client_var('name', self.name)
            if self.ctype != None:
                self.set_client_var('type', self.ctype)
            self.connected = True
        except socket.error:
            print 'failed to connect'
    def close(self):
        self.connected = False
        self.sock.close()
        self.sock = None
    def send(self, data):
        if not self.sock:
            return False
        ok,_ = send_dahi(self.sock, data)
        if not ok:
            self.close()
        return ok
    def recv(self, block=False):
        msg = recv_dahi(self.sock, block=block)
        if msg == None:
            self.close()
        return msg
    def set_client_var(self, name, value, dtype=None):
        if dtype == None:
            dtype = util.get_type(value)
            value = str(value)
        self.send('cliv' + encode_strings([name, dtype, value]))
    def process(self):
        """
        Read data from socket, interpret.  Returns tuple:

        'data', frame_data

        'ctrl', updated_keys_list

        'diec', None

        '?', unknown_command
        """
        data = self.recv(block=False)
        if data == None or data == '':
            return None, None
        cmd = data[:4]
        if cmd == 'ctrl':
            new_controls = decode_json(data[4:])
            updated_keys = []
            for k, v in new_controls.iteritems():
                if self.controls.get(k) != v:
                    # None means delete.
                    if v == None:
                        del self.controls[k]
                    else:
                        self.controls[k] = v
                    updated_keys.append(k)
            return cmd, updated_keys
        elif cmd == 'data':
            d = numpy.array(array.array('f', data[4:]))
            self.data.append(d)
            return cmd, d
        elif cmd == 'diec':
            self.controls['exit'] = True
            return cmd, None
        else:
            return '?', cmd

class dataConsumer(dataClient):
    ctype = 'sink'

class dataProducer(dataClient):
    ctype = 'source'
    def __init__(self, addr, name):
        dataClient.__init__(self, addr=addr, name=name)
        self.options = {}
        self.t_freshen = 0

    def send_data(self, data):
        self.send('data' + data.astype('float32').tostring())

    # Slightly higher level management, for regular shape reminders.
    def post_data(self, data):
        t1 = time.time()
        if self.t_freshen != 0 and t1 - self.t_freshen > 1:
            self.dshape = None
            self.t_freshen = t1
        if self.dshape != data.shape:
            self.post_meta({'data_shape': data.shape})
            self.dshape = data.shape
        self.send_data(data.ravel())
            
    def post_meta(self, info):
        self.send('ctrl' + encode_json(info))
        
if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(util.defaults)
    opts, args = o.parse_args(util.defaults)

    disp = dataProducer(opts.server, 'client')
    print 'I am disp'

