from mheadsup import constants
import util

import numpy

class HeadsupStream:
    props = ['name', 'provider', 'fun_name', 'local_provider',
             'properties']
    def __init__(self, **kwargs):
        for k in self.props:
            v = kwargs.get(k, '')
            setattr(self, k, v)
        if self.properties == '':
            self.properties = {}
        self.subscribers = []
        self.subscriber_data = {}
    def add_subscriber(self, sub, config={}):
        if not sub in self.subscribers:
            self.subscribers.append(sub)
        self.subscriber_data[sub] = config
    def remove_subscriber(self, sub):
        if sub in self.subscriber_data:
            self.subscriber_data.pop(sub)
        if sub in self.subscribers:
            self.subscribers.remove(sub)
    def render_basic(self):
        return dict([(k,getattr(self, k)) for k in self.props])
    def __repr__(self):
        return '<%s %#x (%s)>' % (self.__class__, id(self), self.name)

class StreamListStream(HeadsupStream):
    def __init__(self, *args, **kwargs):
        HeadsupStream.__init__(self, *args, **kwargs)
        self.streams = []
        self.stream_hash = {}
    def add_stream(self, stream):
        # Assume these are HeadsupStreams
        name = stream.name
        if name in self.stream_hash:
            self.remove_stream(name=name)
        self.stream_hash[name] = stream
        self.streams.append(stream)
    def remove_stream(self, stream=None, name=None):
        print 'remove ', stream, name
        if stream is None:
            stream = self.stream_hash.pop(name)
        else:
            del self.stream_hash[stream.name]
        self.streams.remove(stream)
    def remove_provider(self, provider=None, local_provider=None):
        n = 0
        discard = []
        for stream in self.streams:
            keep = (provider is None or stream.provider != provider) and \
                (local_provider is None or  \
                         stream.local_provider != local_provider)
            discard.append(not keep)
        n = sum(discard)
        for s,k in zip(self.streams, discard):
            if k:
                self.remove_stream(s)
        return n
    def remove_subscriber_all(self, subscriber):
        for stream in self.streams:
            stream.remove_subscriber(subscriber)

    def render(self):
        # Encapsulate
        sdata = [x.render_basic() for x in self.streams]
        data = {'purpose': 'stream listing',
                'n_streams': len(self.streams),
                'stream_list': sdata}
        return data
    def parse(self, data):
        msg = data.json_data
        if msg['purpose'] != 'stream_listing':
            return False, "'purpose' != 'stream_listing'"
        self.streams = {}
        for stream in msg['stream_list']:
            name = stream['name']
            self.streams[name] = HeadsupStream(**stream)
        print "streams are now: "
        for s in self.streams:
            print s['name'], s['fun_name']


#
# Message handlers
#
# These are smart at interpreting packets from certain streams.
#
# They should expose the interface defined in _MessageHandler
#

class _MessageHandler:
    def handle(self, addr, data):
        """
        Accepts a decoded address and data objects.  Determines
        whether it should handle the packet.  Handles the packet.

        Returns:
           processed, addr, data

        where processed is True or False depending on whether the
        Handler has recognized and processed the packet.
        """
        return False, addr, data


class ServerMessageHandler:
    """
    Handler for clients that processes messages from the server.
    Includes initial connection negotiation, termination requests,
    etc.
    """
    def __init__(self, parent=None):
        self.status = 'waiting'
        self.weirds = 0
        self.parent = parent

    def handle(self, addr, data):
        # Only take messages from the local server.
        if addr.name != constants.CLIENT_CONTROL_STREAM:
            return False, addr, data
        msg = data.json_data
        msg_class = msg['message_class']
        if msg_class == 'connection_status':
            self.status = msg['connection_standing']
            if 'client_name' in msg:
                self.parent.name = msg['client_name']
            if self.status == 'terminated':
                self.status = 'server_close'
        elif msg_class == 'pink_slip':  # deprecated...
            self.status = 'server_close'
        else:
            self.weirds += 1
            print 'unhandled client control message'
        return True, addr, data


class StreamListStreamHandler:
    """
    Maintain a list of streams available on a given server.
    """
    def __init__(self, server_stream_name='stream_list'):
        self.streams = []
        self.stream_name = server_stream_name
        self.changes = 0
    def handle(self, addr, data):
        if addr.name != self.stream_name:
            return False, addr, data
        msg = data.json_data
        self.changes = 0
        current_names = [s.name for s in self.streams]
        current_active = [False for s in self.streams]
        for stream in msg['stream_list']:
            stream = HeadsupStream(**dict([(str(k), v)
                                           for k,v in stream.items()]))

            if stream.name in current_names:
                i = current_names.index(stream.name)
                old_stream = self.streams[i]
                self.streams[i] = stream
                current_active[i] = True
            else:
                self.streams.append(stream)
                current_active.append(True)
                self.changes += 1
        self.changes += sum([not x for x in current_active])
        self.streams = [x for x,a in zip(self.streams, current_active) if a]
            
        return True, addr, data

class DataHandler:
    def __init__(self, stream_name=None):
        self.frames = []
        self.stream_name = stream_name
        self.info = {}
        self.info_update = True

    def handle(self, addr, data):
        if addr.name != self.stream_name:
            return False, addr, data
        msg = data.json_data
        if addr.type == 'data':
            numpy_data = numpy.fromstring(data.bin_data,
                                          dtype=msg['data_type']).\
                reshape(msg['data_shape'])
            self.frames.append(numpy_data)
            if len(self.frames) > 100:
                self.frames.pop(0)
        elif addr.type == 'notify':
            #print msg
            if 'info_set' in msg:
                self.info = msg['info_set']
            elif 'info_update' in msg:
                self.info.update(msg['info_update'])
            self.info_update = True
        else:
            return False, addr, data
        return True, addr, data


class DataSourceControlHandler:
    def __init__(self, stream_name):
        self.stream_name = stream_name
        self.do_update = False

    def handle(self, addr, data):
        if addr.name != self.stream_name:
            return False, addr, data
        msg = data.json_data
        if 'update' in msg:
            self.do_update = True
        return True, addr, data
            
