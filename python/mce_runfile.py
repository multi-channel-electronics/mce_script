class BadRunfile(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MCERunfile:
    def __init__(self, filename=None):
        self.filename = filename
        self.data = {}
        if filename != None:
            self.Read(filename)

    def Read(self, filename, ignore_dups=True):
        f = open(filename, "r")
        lines = f.readlines()
        block_name = None
        block_data = {}
        block_skip = False
        self.data = {}

        for l in lines:
            key, data = runfile_break(l)
            if key == None: continue

            if key[0] == '/':
                if (block_name != key[1:]):
                    raise BadRunfile('closing tag out of place')
                if data != '':
                    raise BadRunfile('closing tag carries data')
                if block_skip:
                    block_skip = False
                else:
                    self.data[block_name] = block_data
                block_name = None
                block_data = {}
            elif block_name == None:
                if data == None or data == '':
                    block_name = key
                    if self.data.has_key(key):
                        if ignore_dups:
                            block_skip = True
                            continue
                        raise BadRunfile('duplicate block "'+key+'"')
                else:
                    raise BadRunfile('key outside of block!')
            else:
                block_data[key] = data
        return self.data
    
    def Item(self, block, key, array=True, type='string'):
        if not self.data.has_key(block) or not self.data[block].has_key(key):
            return None
        data = self.data[block][key]
        if type=='float':
            f = [float(s) for s in data.split()]
            if not array and len(f) == 0: return f[0]
            return f
        if type=='int':
            f = [int(s) for s in data.split()]
            if not array and len(f) <= 1: return f[0]
            return f
        if type!='string':
            print 'Unknown type "%s", returning string.' % type
        if array:
            return data.split()
        return data

    def Item2d(self, block, key_format, array=True, type='string',
               first = 0, count = None):
        done = False
        result = []
        row = first
        while not done:
            g = self.Item(block, key_format % row, array=array, type=type)
            if g == None:
                break
            result.append(g)
            row = row + 1
            if count != None and row - first == count:
                break
        return result

    def __getitem__(self, key):
        return self.data[key]


def runfile_break(s):
    reform = ' '.join(s.split())
    words = reform.split('>')
    n_words = len(words)
    
    if n_words == 0 or words[0] == '':
        return None, None

    if words[0][0] == '#':
        return None, None

    if words[0][0] != '<':
        raise BadRunfile(s)
    
    key = words[0][1:]
    data = ' '.join(words[1:])

    return key, data
