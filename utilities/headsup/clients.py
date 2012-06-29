from nets import *
import util

import numpy

class dataClient:
    ctype = None
    name = None
    connected = False
    def __init__(self, addr=None, name=None):
        if name != None:
            self.name = name
        if addr != None:
            self.connect(addr)
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
    def send(self, data):
        send_dahi(self.sock, data)
    def recv(self, block=False):
        return recv_dahi(self.sock, block=block)
    def set_client_var(self, name, value, dtype=None):
        if dtype == None:
            dtype = util.get_type(value)
            value = str(value)
        self.send('cliv' + encode_strings([name, dtype, value]))

class dataConsumer(dataClient):
    ctype = 'sync'
    controls = {}
    data = []
    def __init__(self, addr, name):
        dataClient.__init__(self, addr=addr, name=name)
    def process(self):
        data = self.recv(block=False)
        if data == None or data == '':
            return None, None
        cmd = data[:4]
        if cmd == 'ctrl':
            key, dtype, value = decode_strings(data[4:])
            value = util.casts[dtype](value)
            self.controls[key] = value
            return cmd, key
        elif cmd == 'data':
            d = numpy.array(array.array('f', data[4:]))
            self.data.append(d)
            return cmd, d
        else:
            return '?', data

class dataProducer(dataClient):
    ctype = 'source'
    def __init__(self, addr, name):
        dataClient.__init__(self, addr=addr, name=name)
        self.options = {}
        self.freshen = 0
    def send_control(self, name, value, dtype=None):
        if dtype == None:
            dtype = util.get_type(value)
            value = str(value)
        self.send('ctrl' + encode_strings([name, dtype, value]))
    def send_data(self, data):
        self.send('data' + data.astype('float32').tostring())

    # Slightly higher level management, for regular shape reminders.
    def post_data(self, data):
        if self.freshen <= 0:
            self.dshape = None
            self.freshen = self.options.get('refreshen', 100)
        if self.dshape != data.shape:
            self.send_control('nrow', data.shape[0])
            self.send_control('ncol', data.shape[1])
            self.dshape = data.shape
        self.send_data(data.ravel())
        self.freshen -= 1
            
