import sys
import socket
import time
import array
import SocketServer
import errno

import nets, util
from nets import *

"""
Implement a server that can pass data from distributors to plotters.

Encapsulating protocol:
  'dahi' xxxx payload...
where xxxx is the 32-bit payload size, in bytes.  Probably LSB first.

Then:
  'type' 'x...' <- register client type (32 bytes)
  'name' 'x...' <- register client name (32 bytes)
  'list'        <- request list of clients. (returns parsable string)
  'diex'        <- exit
  'serv'        <- set server variable
"""

defaults = util.defaults.copy()
defaults.update({
    'client_name': 'server',
    })


class dataHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        me = self.request
        dd.add(me)
        me.setblocking(0.5)
        while True:
            while True:
                op, data = dd.get_action(me)
                if op == None:
                    break
                if op == 'send':
                    ok, err = nets.send_dahi(me, data)
                    if err == errno.EPIPE:
                        break
                if op == 'close':
                    break
            data = nets.recv_dahi(me, block=False)
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
            self.addr = nets.decode_address(addr)
        self.clients = {}
        self.actions = {}
        self.sources = {}
        self.syncs = {}
        self._id = 0

    def serve(self):
        try:
            self.server = thServer(self.addr, dataHandler)
            self.server.serve_forever()
        except socket.error as err:
            print "Failed to start server, error %i (%s)" % err.args[:2]

    def post_action(self, conn, act, data=None, quick=False):
        """
        Register an action for a client thread to perform later.
        """
        data = (act, data)
        if quick:
            self.actions[conn].insert(0, data)
        else:
            self.actions[conn].append(data)

    #
    # Callbacks for the TCPServer threads
    #

    def add(self, conn):
        """
        Add the new socket conn to the list of clients.
        """
        self._id += 1
        self.clients[conn] = {'conn': conn, 'id': self._id,
                              'name': '', 'type': ''}
        self.actions[conn] = []

    def remove(self, conn):
        """
        Remove socket conn from list of clients.
        """
        self.actions.pop(conn)
        self.clients.pop(conn)

    def get_action(self, conn):
        """
        If there is outstanding data for conn to write, provide it.
        """
        try:
            return self.actions[conn].pop(0)
        except:
            return None, None

    def data(self, conn, data):
        """
        Process the data packet from conn.
        """
        info = self.clients[conn]
        cmd = data[:4]
        if cmd == 'diex':
            for client in self.clients.keys():
                self.post_action(client, 'close', quick=True)
            self.server.shutdown()
        elif cmd == 'cliv':
            # Set client variables (name, type, sync)
            key, dtype, value = decode_strings(data[4:])
            info[key] = util.casts[dtype](value)
        elif cmd == 'list':
            omit_keys = ['conn']
            list_data = []
            for c in self.clients.values():
                d = c.copy()
                for k in omit_keys:
                    d.pop(k)
                list_data.append((c['id'], d))
            list_data = zip(*sorted(list_data))[1]
            self.post_action(conn, 'send', 'list'+nets.encode_json(list_data))
        # Sources send control and data packets, pass them on to
        # listeners.
        elif cmd in ['ctrl','data']:
            for c in self.clients.keys():
                info = self.clients[c]
                if info.get('type') == 'sync':
                    self.post_action(c, 'send', data)
        else:
            print 'Whatever, "%s"' % data[:4]


if __name__ == '__main__':
    o = util.upOptionParser()
    o.add_standard(defaults)
    o.add_option('--kill',action='store_true')
    o.add_option('--tunnel')
    opts, args = o.parse_args(defaults)
    
    if opts.tunnel:
        import os
        host, port = nets.decode_address(opts.server)
        os.system('ssh -N -L%i:%s:%i %s' % \
                      (opts.port, opts.host, opts.port, opts.tunnel))
                  
    if opts.kill:
        import clients
        killer = clients.dataClient(opts.server)
        killer.send('diex')
        sys.exit(0)

    dd = dataDistributor(opts.server)
    dd.serve()
