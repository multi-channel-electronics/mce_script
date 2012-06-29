import clients

display_defaults = {
    'autoscale': True,
    'zrange': (-1000,1000),
    }

class displayController(dict, clients.dataProducer):
    def __init__(self, addr, name='dispctrl', field=None):
        dict.__init__(self)
        clients.dataProducer.__init__(self, addr, name)
        self.update(display_defaults)

    def post_some(self, keys):
        packet = {}
        for k in keys:
            packet[k] = self[k]
        self.post_meta(packet)
    
    #
    # High level display control
    #

    def autoscale(self, value=None):
        if value == None:
            return self['autoscale']
        self['autoscale'] = value
        self.post_some(['autoscale'])

    def zrange(self, min=None, max=None):
        post = False
        if min != None:
            self['zrange'] = min
            post = True
        if max != None:
            self['zrange'] = max
            post = True
        if post:
            self.post_some(['zrange'])
        return self['zrange']

