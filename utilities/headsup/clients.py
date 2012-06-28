from nets import *

import numpy

casts = {
    'int': int,
    'float': float,
    'str': str,
}
    
class dataClient:
    ctype = None
    name = None
    def __init__(self, addr=None, name=None):
        if name != None:
            self.name = name
        if addr != None:
            self.connect(addr)
    def connect(self, addr=None):
        if addr != None:
            self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(decode_address(self.addr))
        self.sock.setblocking(0.5)
        if self.name != None:
            self.send('name%s\x00' % self.name)
        if self.ctype != None:
            self.send('type%s\x00' % self.ctype)
    def send(self, data):
        send_dahi(self.sock, data)
    def recv(self, block=False):
        return recv_dahi(self.sock, block=block)

class dataConsumer(dataClient):
    ctype = 'plotter'
    controls = {}
    data = []
    def __init__(self, addr, name):
        dataClient.__init__(self, addr=addr, name=name)
    def process(self):
        data = self.recv(block=False)
        if data == '':
            return None, None
        cmd = data[:4]
        if cmd == 'ctrl':
            key, dtype, value = decode_strings(data[4:])
            value = casts[dtype](value)
            self.controls[key] = value
            return cmd, key
        elif cmd == 'data':
            d = numpy.array(array.array('f', data[4:]))
            self.data.append(d)
            return cmd, d
        else:
            return '?', data

class dataProducer(dataClient):
    ctype = 'producer'
    def __init__(self, addr, name):
        dataClient.__init__(self, addr=addr, name=name)
        self.options = {}
        self.freshen = 0
    def send_control(self, name, dtype, value):
        self.send('ctrl' + encode_strings([name, dtype, str(value)]))
    def send_data(self, data):
        self.send('data' + data.astype('float32').tostring())

    # Slightly higher level management, for regular shape reminders.
    def post_data(self, data):
        if self.freshen <= 0:
            self.dshape = None
            self.freshen = self.options.get('refreshen', 100)
        if self.dshape != data.shape:
            self.send_control('nrow', 'int', data.shape[0])
            self.send_control('ncol', 'int', data.shape[1])
            self.dshape = data.shape
        self.send_data(data.ravel())
        self.freshen -= 1
            
