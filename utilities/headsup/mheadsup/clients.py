from mheadsup import nets, streams, constants
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
        if not self.sock:
            return None
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


class HeadsupClient:
    name = None
    connected = False
    client_control_handler = None
    stream_list_handler = None
    
    def __init__(self, addr=None, name=None):
        self.handlers = []
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
            self.send('setv')
            self.connected = True
        except socket.error:
            print 'failed to connect'
        # Replace the server message and stream list handlers
        self.client_control_handler = \
            self.replace_handler(streams.ServerMessageHandler(parent=self),
                                 self.client_control_handler)
        self.stream_list_handler = \
            self.replace_handler(streams.StreamListStreamHandler(),
                                 self.stream_list_handler)
        for i in range(20):
            ok, _,_ = self.do_receive()
            if ok:
                if self.client_control_handler.status == 'accepted':
                    break
            time.sleep(.1)
        else:
            print 'timed-out!'
            return
        self.subscribe('stream_list')
        
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
        if not self.sock:
            return None
        msg = recv_dahi(self.sock, block=block)
        if msg == None:
            self.close()
        return msg

    def send_json(self, stream, data, type='notify'):
        encoder = nets.packetFormatV1
        ok, data = encoder.encode_packet(type, stream,
                                         self.name, '',
                                         data
                                         )
        self.send(data)

    def subscribe(self, stream, server_stream=None):
        """
        Issue a subscription request to the server.
        """
        if server_stream == None:
            server_stream = constants.CLIENT_CONTROL_STREAM
        encoder = nets.packetFormatV1
        ok, data = encoder.encode_packet('control', server_stream,
                                         self.name, '',
                                         {'request': 'subscribe',
                                          'stream_name': stream},
                                         )
        self.send(data)

    def unsubscribe(self, stream, server_stream=None):
        """
        Tell the server to stuff it.
        """
        if server_stream == None:
            server_stream = constants.CLIENT_CONTROL_STREAM
        encoder = nets.packetFormatV1
        ok, data = encoder.encode_packet('control', server_stream,
                                         self.name, '',
                                         {'request': 'unsubscribe',
                                          'stream_name': stream},
                                         )
        self.send(data)

    def register_streams(self, stream_list, server_stream=None):
        """
        Register a single control stream with the server. 
        """
        if server_stream == None:
            server_stream = constants.CLIENT_CONTROL_STREAM
        encoder = nets.packetFormatV1
        stream_data = [s.render_basic() for s in stream_list]
        ok, data = encoder.encode_packet('control', server_stream,
                                         self.name, 'trgtclient',
                                         {'request': 'register_streams',
                                          'streams': stream_data},
                                         )
        self.send(data)

    def do_receive(self, do_handle=True):
        """
        Check socket for data.  Pass it to the handlers.  Returns

             handled, address, data

        where handled is True if someone claimed ownership of the
        packet, address and data are the packet address and payload.
        """
        data = self.recv(block=False)
        if data == None or data == '':
            return True, None, None
        encoder = nets.packetFormatV1
        ok, addr, data = encoder.decode_packet(data)
        if not ok:
            print 'Invalid packet.'
            return False, None, None
        if not do_handle:
            return False, addr, data
        return self.handle(addr, data)

    def handle(self, addr, data):
        ok = False
        for handler in self.handlers:
            ok, _,_ = handler.handle(addr, data)
            if ok:
                break
        return ok, addr, data

    def replace_handler(self, new_handler, old_handler):
        if old_handler in self.handlers:
            i = self.handlers.index(old_handler)
            self.handlers[i] = new_handler
        else:
            self.handlers.append(new_handler)
        return new_handler


class HeadsupDataSource(HeadsupClient):
    data_stream = None
    notify_stream = None
    control_stream = None
    control_handler = None
    geometries = None

    def __init__(self, *args, **kwargs):
        HeadsupClient.__init__(self, *args, **kwargs)
        self.info = [True, {}]

    def register_basic_streams(self):
        prefix = self.name
        self.data_stream = streams.HeadsupStream(
            name=prefix + '_data', type='data')
        self.control_stream = streams.HeadsupStream(
            name=prefix + '_control', type='control')
        self.notify_stream = streams.HeadsupStream(
            name=prefix + '_notify', type='notify')
        self.register_streams([self.data_stream, self.control_stream,
                               self.notify_stream])
        self.control_handler = self.replace_handler(
            streams.DataSourceControlHandler(self.control_stream.name),
            self.control_handler)

    # For the notify stream...
    def update_info(self, new_info, replace=False, trigger_notify=True):
        if replace:
            self.info[1] = {}
        self.info[0] = True
        self.info[1].update(new_info)
        if trigger_notify:
            print 'sending ', self.info[1]
            self.send_json(self.notify_stream.name, {'info_update': self.info[1]})

    def post_data(self, data):
        encoder = nets.packetFormatV1
        json_data = {'data_packing': 'simple',
                     'data_shape': data.shape,
                     'data_type': data.dtype.name}
        if data == None:
            bin_data = None
        else:
            bin_data = data.tostring()
        
        ok, data = encoder.encode_packet('data', self.data_stream.name,
                                         self.name, '',
                                         json_data,
                                         bin_data
                                         )
        self.send(data)

    def set_geometries(self, geometries):
        print 'SET GEOM'
        data = {'geometries': [g.encode() for g in geometries]}
        self.update_info(data)

    def do_receive(self):
        ok, addr, data = HeadsupClient.do_receive(self)
        if not ok:
            return ok, addr, data
        ch = self.control_handler
        if ch != None:
            if ch.do_update:
                self.update_info({},trigger_notify=True)
                ch.do_update = False
        return ok, addr, data


class HeadsupDataConsumer(HeadsupClient):
    notify_stream = None
    control_stream = None
    data_handler = None
    control_handler = None

    def connect(self, *args, **kwargs):
        HeadsupClient.connect(self,*args, **kwargs)
        
    def subscribe_data(self, prefix=None, data_stream=None,
                       notify_stream=None, control_stream=None):
        self.unsubscribe_data()
        self.data_handler = \
            self.replace_handler(streams.DataHandler(prefix, data_stream,
                                                     notify_stream, control_stream),
                                 self.data_handler)
        self.subscribe(self.data_handler.data_stream)
        self.subscribe(self.data_handler.notify_stream)
        self.send_json(self.data_handler.control_stream,
                       {'update': self.name}, type='control')

    def unsubscribe_data(self):
        if self.data_handler == None:
            return False
        self.unsubscribe(self.data_handler.data_stream)
        self.unsubscribe(self.data_handler.notify_stream)
        self.unsubscribe(self.data_handler.control_stream)
        return True

    def register_basic_streams(self):
        prefix = self.name
        self.control_stream = streams.HeadsupStream(
            name=prefix + '_control', type='control')
        self.notify_stream = streams.HeadsupStream(
            name=prefix + '_notify', type='notify')
        self.register_streams([self.data_stream, self.control_stream,
                               self.notify_stream])
        self.control_handler = self.replace_handler(
            streams.DataDisplayInfoHandler(self.control_stream.name),
            self.control_handler)
        

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
    o.add_standard(util.get_defaults())
    opts, args = o.parse_args()

    disp = dataProducer(opts.server, 'client')
    print 'I am disp'

