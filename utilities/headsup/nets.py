import sys
import socket
import time
import array
import numpy
import errno
import json

def send_dahi(sock, data, tag=None):
    n = len(data)
    pre = 'dahi' + array.array('i', [n]).tostring()
    # Great
    data = pre + data
    n = 0
    while n < len(data):
        try:
            n += sock.send(data[n:])
        except socket.error as err:
            return False, err
    return True, 0

def recv_wrapped(sock, n):
    """
    Attempt to read n bytes from sock.  Returns tuple
       (ok, n_read, data)
    """
    ok, data = True, ''
    
    try:
        data = sock.recv(n)
        if data == '':
            ok = False
    except socket.error as err:
        if err.args[0] != errno.EAGAIN:
            ok = False
    return ok, len(data), data
    
def recv_dahi(sock, block=True):
    """
    Returns None on error; string otherwise.

    Return string will be '', or a complete and valid dahi packet.
    """
    n_read = 0
    header = False
    data = ''
    n = 8
    while True:
        ok, _n, new_data = recv_wrapped(sock, n-n_read)
        if not ok:
            return None
        if _n == 0:
            if n_read == 0 and not block:
                return ''
            time.sleep(.01)
            continue
        n_read += _n
        data += new_data
        if n_read == n:
            if header:
                return data[8:]
            else:
                if data[:4] != 'dahi':
                    return ''
                # Payload size
                n += array.array('i', data[4:])[0]
                header = True
            
def encode_json(d):
    return 'json\x00' + json.dumps(d)

def decode_json(d):
    a, b = d.split('\x00')
    if not a == 'json':
        raise ValueError, "does not appear to be a jsondict"
    return json.loads(b)


def encode_strings(ss):
    return '\x00'.join(ss) + '\x00'

def decode_strings(s, n=-1):
    if n == -1:
        return s.split('\x00')[:-1]
    return s.split('\x00', n)

def decode_address(addr):
    if isinstance(addr, basestring):
        host, port = addr.split(':')
        port = int(port)
        return (host, port)
    return addr

