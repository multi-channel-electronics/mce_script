from mheadsup import nets, streams, constants
import util

import numpy


class HeadsupClient:
    name = None
    connected = False
    client_control_handler = None
    stream_list_handler = None
    encoder = None
    
    def __init__(self, addr=None, name=None, log=None,
                 verbosity=None):
        self.handlers = []
        self.connected = False
        self.encoder = nets.packetFormatV1
        if log == None:
            log = util.logger(verbosity=verbosity)
        self.log = log
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
        self.sock, err, msg = nets.get_socket(self.addr)
        if err != 0:
            self.log('Failed to connect to server; error %i (%s)' % \
                (err, msg))
            return False

        self.sock.settimeout(0.1)
        self.connected = True

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
            self.log('timed-out!')
            return
        self.subscribe('stream_list')
        
    def close(self):
        self.connected = False
        self.sock.close()
        self.sock = None

    def send(self, data):
        if not self.sock:
            return False
        ok,_ = nets.send_dahi(self.sock, data)
        if not ok:
            self.close()
        return ok

    def recv(self, block=False):
        if not self.sock:
            return None
        msg = nets.recv_dahi(self.sock, block=block)
        if msg == None:
            self.close()
        return msg

    def send_json(self, stream, data, ptype='notify',
                  destination=''):
        ok, data = self.encoder.encode_packet(ptype, stream,
                                              self.name, destination,
                                              data
                                              )
        self.send(data)

    def subscribe(self, stream, server_stream=None):
        """
        Issue a subscription request to the server.
        """
        if server_stream == None:
            server_stream = constants.CLIENT_CONTROL_STREAM
        ok, data = self.encoder.encode_packet('control', server_stream,
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
        ok, data = self.encoder.encode_packet('control', server_stream,
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
        stream_data = [s.render_basic() for s in stream_list]
        ok, data = self.encoder.encode_packet('control', server_stream,
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
        ok, addr, data = self.encoder.decode_packet(data)
        if not ok:
            self.log('Invalid packet.')
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
        if self.client_control_handler != None and \
                self.client_control_handler.status == 'server_close':
            self.log('Received termination from server.')
            self.close()
        return ok, addr, data

    def replace_handler(self, new_handler, old_handler):
        if old_handler in self.handlers:
            i = self.handlers.index(old_handler)
            self.handlers[i] = new_handler
        else:
            self.handlers.append(new_handler)
        return new_handler


class HeadsupDataSource(HeadsupClient):
    stream = None
    control_handler = None
    geometries = None

    def __init__(self, *args, **kwargs):
        HeadsupClient.__init__(self, *args, **kwargs)
        self.info = [True, {}]

    def register_basic_streams(self):
        prefix = self.name
        self.stream = streams.HeadsupStream(name=self.name + '_stream',
                                            properties={'data_stream': True})
        self.register_streams([self.stream])
        self.control_handler = self.replace_handler(
            streams.DataSourceControlHandler(self.stream.name),
            self.control_handler)

    # For the notify stream...
    def update_info(self, new_info, replace=False, trigger_notify=True):
        if replace:
            self.info[1] = {}
        self.info[0] = True
        self.info[1].update(new_info)
        if trigger_notify:
            self.log('issuing notify' + ' '.join(self.info[1].keys()))
            self.send_json(self.stream.name, {'info_update': self.info[1]})

    def post_data(self, data):
        json_data = {'data_packing': 'simple',
                     'data_shape': data.shape,
                     'data_type': data.dtype.name}
        if data == None:
            bin_data = None
        else:
            bin_data = data.tostring()
        
        ok, data = self.encoder.encode_packet('data', self.stream.name,
                                              self.name, '',
                                              json_data,
                                              bin_data
                                              )
        self.send(data)

    def set_geometries(self, geometries):
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
    stream = None
    data_handler = None
    control_handler = None

    def connect(self, *args, **kwargs):
        HeadsupClient.connect(self,*args, **kwargs)
        
    def subscribe_data(self, stream_name):
        self.unsubscribe_data()
        self.data_handler = \
            self.replace_handler(streams.DataHandler(stream_name),
                                 self.data_handler)
        self.subscribe(self.data_handler.stream_name)
        self.send_json(self.data_handler.stream_name,
                       {'update': self.name}, ptype='control')

    def unsubscribe_data(self):
        if self.data_handler == None:
            return False
        self.unsubscribe(self.data_handler.stream_name)
        return True

    def register_basic_streams(self):
        prefix = self.name
        self.stream = streams.HeadsupStream(name=self.name + '_stream')
        self.register_streams([self.stream])
        self.control_handler = self.replace_handler(
            streams.DataDisplayInfoHandler(self.stream.name),
            self.control_handler)
        

if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(util.get_defaults())
    opts, args = o.parse_args()

    disp = dataProducer(opts.server, 'client')
    disp.log('I am disp')

