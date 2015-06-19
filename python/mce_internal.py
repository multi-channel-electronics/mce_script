"""
Classes and functions for supporting MCE internal ramps (see
scripts/mce_internal_ramp and scripts/mce_awg).
"""

import subprocess as sp
import re
import sys,os

try:
    from pymce.compat import old_mce as mce
except ImportError:
    print 'Could not load mce module; mce commanding will be disabled.'

def abort_msg(text, error=20):
    sys.stderr.write('Error: %s\n' % text)
    sys.exit(error)


            
# Help the user find standard stages easily.
stage_map = {
    'sa_fb': ('sa', 'fb'),
    'sa_bias': ('sa', 'bias'),
    'sq2_fb': ('sq2', 'fb'),
    'sq2_bias': ('sq2', 'bias'),
    'sq1_fb': ('sq1', 'fb_const'),
    'sq1_bias': ('ac', 'on_bias'),
    'tes_bias': ('tes', 'bias'),
    'heater': ('heater', 'bias'),
}


class physicalMap:
    def __init__(self, card_name, param_name, param_id, card_ids):
        self.card, self.param, self.p_id, self.c_ids = \
            card_name, param_name, param_id, card_ids
    @classmethod
    def decode(cls, line):
        #'physical   rca        num_rows             0x31  2 cards: 0x03 0x04'
        w = line.split()
        card, param, p_id = w[1],w[2],int(w[3],0)
        c_ids = [int(x,0) for x in w[6:]]
        return cls(card, param, p_id, c_ids)

class virtualMap:
    def __init__(self, card_name, param_name, maps):
        self.card, self.param, self.maps = \
            card_name, param_name, maps
    @classmethod
    def decode(cls, line):
        #'virtual  sq1   fb_const  maps: [(0,8)->('rc1 fb_const'+ 0)] [(8,8)->('rc2 fb_const'+ 0)]'
        w = line.split()
        card, param = w[1], w[2]
        # Recreate an equivalent mapping statement :P
        maps_line = ' '.join(w[4:])
        # Extract each string between square brackets; [...] [...]
        map_strs = re.findall('(?:\[)([^\[\]]*)(?:\])', maps_line)
        maps = []
        for ms in map_strs:
            # Pull out the start, length, param address, and offset:
            m = re.match( r'(?:\()([0-9]+)(?:,)([0-9]+)(?:\)->\(\')(.*)(?:\'\+\ *)(.*)(?:\))',
                          ms).groups()
            c, p = m[2].split()
            maps.append((int(m[0],0), int(m[1],0), c, p, int(m[3],0)))
        return cls(card, param, maps)

class configAnalysis:
    """
    Decode output of mce_status -g.
    """
    def __init__(self, load=True):
        self.phys = []
        self.virt = []
        if load:
            self.load()

    def load(self, command=None, lines=None):
        if command == None:
            command = ['/usr/mce/bin/mce_status','-g']
        if lines == None:
            p = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
            lines, errs = p.communicate()
            lines = lines.split('\n')
        # Decode the lines
        for l in lines:
            w = l.split()
            if len(w) == 0 or w[0][0] == '#': continue
            if w[0] == 'physical':
                self.phys.append(physicalMap.decode(l))
            elif w[0] == 'virtual':
                self.virt.append(virtualMap.decode(l))
        # That will do
        return lines

    def get_ramp_params(self, card, param, start=0, count=None, _recursion=0):
        if _recursion > 10:
            return False, 'maximum recursion depth exceeded!'
        # First search physical cards:
        for p in self.phys:
            if p.card == card and p.param == param:
                if len(p.c_ids) > 1:
                    return False, 'physical parameter "%s %s" is broadcast to multiple cards.'%\
                        (card,param)
                # Good candidate, but check the index limits.
                if start != 0:
                    return False, 'parameter matched but starting index is offset by %i' % start
                # Great; return card, parameter,  ID.
                return True, (p.c_ids[0], p.p_id, count)
        # Next search virtual candidates
        for v in self.virt:
            if v.card == card and v.param == param:
                # See if any of the maps work.
                results = []
                if len(v.maps) > 1 and count == None:
                    return False, 'must specify parameter count for mapped non-trivial virtual map'
                for m in v.maps:
                    _start, _count, c, p, offset = m
                    if count != None and count > _count:
                        continue
                    # Recurse until we hit a physical parameter.
                    results.append( self.get_ramp_params(c, p, _start-start, _count,
                                                         _recursion=_recursion+1) )
                if len(results) == 0:
                    return False, 'no match found while traversing virtual map; '\
                        'try restricting your parameter to a single readout card.'
                ok = [(r,r1) for r,r1 in results if r]
                if len(ok) > 1:
                    return False, 'multiple results, restrict your search to a single readout card.'
                if len(ok) == 1:
                    return ok[0]
                return False, 'no matches found'
        # That's all we got
        return False, 'not found'



"""
Arbitrary waveform generation support.
"""

AWG_MAX_DATA = 8192
AWG_BLOCK_SIZE = 32

class awgAccessor:
    """
    Read and write to the CC AWG data area.
    """
    def __init__(self, mce):
        self.mce = mce
    def read(self, n=None, reset=True):
        if n == None:
            n = self.mce.read('cc', 'awg_sequence_length')[0]
        if n > AWG_MAX_DATA:
            n = AWG_MAX_DATA
            print 'Limiting read to %i words' % n
        addr = 0
        if not reset:
            addr = self.get_address()
        data = []
        while n>0:
            self.set_address(addr)
            _n = min(AWG_BLOCK_SIZE, n)
            d = self.mce.read('cc', 'awg_data', _n)
            data.extend(d)
            n -= _n
            addr += _n
        return data
    def write(self, data, reset=True, set_length=True):
        data = map(int, data)   # cast for safety
        n = len(data)
        if n > AWG_MAX_DATA:
            n = AWG_MAX_DATA
            print 'Limiting write to %i words' % n
        if set_length:
            self.mce.write('cc', 'awg_sequence_length', [int(n)])
        if reset:
            addr = 0
        else:
            addr = self.get_address()
        i = 0
        while i<n:
            self.set_address(addr+i)  # bug, MCE over-advances addr
            _n = min(AWG_BLOCK_SIZE, n-i)
            self.mce.write('cc', 'awg_data', data[i:i+_n])
            i += _n
    def set_address(self, i):
        return self.mce.write('cc', 'awg_addr', [int(i)])
    def get_address(self):
        return self.mce.read('cc', 'awg_addr')[0]

