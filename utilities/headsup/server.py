import sys
import socket
import time
import array
import SocketServer
import errno

import nets
from nets import *

"""
Implement a server that can pass data from distributors to plotters.

Encapsulating protocol:
  'dahi' xxxx payload...
 where xxxx is the 32-bit packet size, in bytes.  Probably LSB first.

Then:
  'type' 'x...' <- register client type (32 bytes)
  'name' 'x...' <- register client name (32 bytes)
  'list'        <- request list of clients. (returns parsable string)
  'diex'        <- exit
"""

class dataHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = ''
        me = self.request
        dd.add(me)
        me.setblocking(0.5)
        while True:
            while True:
                action = dd.get_action(me)
                if action == None:
                    break
                send_dahi(me, action)
            data = recv_dahi(me, block=False)
            if data == None:
                break
            if data == '':
                time.sleep(.5)
                continue
            dd.data(me, data)
        dd.remove(me)

class thServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class dataDistributor:
    def __init__(self, addr=None):
        if addr != None:
            self.addr = decode_address(addr)
        self.clients = {}
        self.actions = {}
        self._id = 0
    def serve(self):
        self.server = thServer(self.addr, dataHandler)
        self.server.serve_forever()
    def add(self, conn):
        self._id += 1
        self.clients[conn] = {'conn': conn, 'id': self._id}
        self.actions[conn] = []
    def remove(self, conn):
        self.actions.pop(conn)
        self.clients.pop(conn)
    def get_action(self, conn):
        try:
            return self.actions[conn].pop(0)
        except:
            return None
    def data(self, conn, data):
        info = self.clients[conn]
        cmd = data[:4]
        if cmd == 'diex':
            self.server.shutdown()
        elif cmd == 'type':
            info['type'] = decode_strings(data[4:])[0]
        elif cmd == 'name':
            info['name'] = decode_strings(data[4:])[0]
        elif cmd == 'list':
            data = []
            for client in self.clients.values():
                data.append((client['id'], client['name'], client['type']))
            data.sort()
            data = ['%i\x00%s\x00%s\x00' % row for row in data]
            data = '\x00'.join(data)
            self.actions[c].append(cmd + data)
        elif cmd in ['ctrl','data']:
            # pass it on...
            for c in self.clients.keys():
                info = self.clients[c]
                if info.get('type') == 'plotter':
                    self.actions[c].append(data)
        else:
            print 'Whatever, "%s"' % data[:4]


if __name__ == '__main__':
    from optparse import OptionParser
    o = OptionParser()
    o.add_option('--kill',action='store_true')
    o.add_option('--tunnel')
    opts, args = o.parse_args()
    
    SRVADR = nets.default_addr

    if opts.tunnel:
        import os
        host, port = nets.decode_address(SRVADDR)
        os.system('ssh -N -L%i:%s:%i %s' % (port, host, port, opts.tunnel))
                  
    if opts.kill:
        import clients
        killer = clients.dataClient(SRVADR)
        killer.send('diex')
        sys.exit(0)

    dd = dataDistributor(SRVADR)
    dd.serve()
