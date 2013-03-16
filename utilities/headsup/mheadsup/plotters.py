import json
import time

import clients
import numpy as np

display_defaults = {
    'autoscale': True,
    'zrange': [-1000,1000],
    'poll_controls': 1,
    }

def mask_to_list(ar):
    return [[int(x) for x in y] for y in ar]



class displayClient(clients.HeadsupDataConsumer):
    """
    Base class for plotters.

    Handles basic messages related to displaying of data.
    Implementation of data display is left to subclasses.
    """
    def __init__(self, addr=None, name=None):
        clients.HeadsupDataConsumer.__init__(self, addr, name)
        self.data_mask = None
        self.last_data = None
        self.controls = {}
        self.controls.update(display_defaults)
        self.texts = textItemList()
        self.texts.append('time_now', 'Time:')
        self.texts.append('time_frame', 'Last frame:')
#        self.texts.append('data_mode', 'Data mode:')
        self.texts.append('autoscale', 'Scaling mode:')
        self.texts.append('zrange_lo', 'Scale:')
        self.texts.append('zrange_hi', '')

    def _get_scale(self, data, update_texts=True):
        # Decide how to convert project the data into the [0,1] range
        # consumed by plotters.  Returns
        #     auto, black, white
        # where auto indicates full autoscale mode; black is the level
        # that should project to 0, white is the data level that
        # should project to 1.
        auto = self.controls.get('autoscale', False)
        black, white = self.controls.get('zrange', (None,None))
        if auto or black == None:
            black = data.min()
        if auto or white == None:
            white = data.max()
        if update_texts:
            self.texts.set_text('zrange_lo', '%.3f' % black)
            self.texts.set_text('zrange_hi', '%.3f' % white)
            self.texts.set_text('autoscale', str(auto))
        return auto, black, white

    def _norm_data(self, data, black, white, mask=None, mask_val=None):
        if mask != None and mask.sum() > 0:
            if mask_val == None:
                mask_val = (black+white)/2
            data[~mask] = mask_val
        data = (data - black) / (white-black)
        data[data<0] = 0
        data[data>1] = 1
        return data

    def update_image(self, *args, **kwargs):
        """
        Updates the image, or some aspect of it (scale, zoom, ...).
        """
        pass # virtual

    def update_texts(self, redraw=None):
        pass # virtual




#
# Needs a rewrite...

class displayController: #(clients.dataProducer, dict):
    """
    This class can be used to control a plot window from a client of
    some kind.  It exposes high-level methods that send display
    control messages to the display clients.
    """

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

    ##
    ## Scale control
    ##
    def autoscale(self, value=None):
        """
        Toggle autoscaling on the display.
        """
        if value == None:
            return self['autoscale']
        self['autoscale'] = value
        self.post_some(['autoscale'])

    def zrange(self, min=None, max=None):
        """
        Set z-range on the display, for when not autoscaling.
        """
        post = False
        if min != None:
            self['zrange'][0] = min
            post = True
        if max != None:
            self['zrange'][1] = max
            post = True
        if post:
            self.post_some(['zrange'])
        return self['zrange']

    ##
    ## Masking is used to remove some array elements from being
    ## included in autoscaling.  This will change.
    ##

    def set_mask(self, mask=None):
        if mask == None:
            return self['mask']
        # json doesn't like numpy's ints.
        self['mask'] = [[int(x) for x in y] for y in mask]
        self.post_some(['mask'])

    def mask_area(self, row=None, col=None, shape=None, unmask=False):
        if 'mask' not in self:
            if shape != None:
                mask = np.zeros(shape, 'bool')
            else:
                print 'Set mask shape first.'
                return False
        else:
            mask = np.asarray(self['mask'], 'bool').transpose()
        if row != None and col != None:
            mask[row, col] = False ^ unmask
        elif row != None:
            mask[row,:] = False ^ unmask
        elif col != None:
            mask[:,col] = False ^ unmask
        else:
            mask[:,:] = False ^ unmask
        self.set_mask(mask_to_list(mask.transpose()))
        
    def unmask_area(self, row=None, col=None, shape=None):
        return self.mask_area(row, col, shape, unmask=True)

    ##
    ## Pixel sets and display maps.
    ##

    def set_pixel_set(self):
        pass


    #
    # Save and restore
    #

    def save(self, filename):
        open(filename,'w').write(json.dumps(self))
    
    def restore(self, filename, update=False):
        if not update:
            self.clear()
        d = json.loads(open(filename).read())
        self.update(d)
        self.post_some(d.keys())

    def get_controls(self, timeout=2.):
        self.set_client_var('poll_controls', 1)
        dt = .1
        for i in range(min(timeout/dt, 1)):
            op, data = self.process()
            if op == 'ctrl':
                break
            time.sleep(dt)
        
    def watch_controls(self, enable=None, loop=False):
        if enable == True:
            return self.set_client_var('monitor_controls', 1)
        if enable == False:
            return self.set_client_var('monitor_controls', 0)
        while self.connected:
            self.process()
            if not loop:
                break
            time.sleep(.2)
            

#
# Assistance for plotters
#

class textItem:
    def __init__(self, name, label, text=None):
        self.name = name
        self.label = label
        self.text = text
        self.changed = text != None
    def set_text(self, text):
        if text != self.text:
            self.text = text
            self.changed = True
    def get_update(self):
        if not self.changed:
            return None, None
        self.changed = False
        return self.label, self.text

class textItemList(dict):
    def __init__(self):
        dict.__init__(self)
        self['_gobj'] = {}
        self['_order'] = []
    def append(self, name, label, text=None):
        self[name] = textItem(name, label, text)
        self['_order'].append(name)
    def set_text(self, name, text):
        if name in self:
            self[name].set_text(text)


#
#
#

class dataScaleProps:
    z_offset = None
    z_range = (None, None)

    # Modes: auto, stretch, fixed
    mode = 'auto'

    trigger_grab_offset = False
    trigger_stretch = False

    last_limits = (0., 0.)

    def rescale_data(self, data, mask=None,
                     clip_vals=None,
                     mask_val=None):
        """
        Transform array data into the range (0,1).
        """
        # Are we supposed to do a re-offset?
        if self.trigger_grab_offset:
            self.z_offset = data.copy()
            self.trigger_grab_offset = False
            if self.mode == 'stretch':
                self.trigger_stretch = True
        # Apply one-time offset
        if self.z_offset != None:
            if data.shape == self.z_offset.shape:
                data = data - self.z_offset
            else:
                self.z_offset = None
        # Only masked pixels enter computation
        if mask != None:
            data_for_lims = data[mask]
        else:
            data_for_lims = data
        # Data limits; these are used for mode='auto'
        scale_lo, scale_hi = data_for_lims.min(), data_for_lims.max()

        # Scale reset?
        if self.trigger_stretch:
            self.mode = 'stretch'
            self.trigger_stretch = False
            self.z_range = scale_lo, scale_hi
        # Determine hi and lo ends of the color scale
        if self.mode == 'stretch':
            # In stretch mode, let the data drag the limits
            self.z_range = min(scale_lo, self.z_range[0]), \
                max(scale_hi, self.z_range[1])
            scale_lo, scale_hi = self.z_range
        elif self.mode == 'fixed':
            range_lo, range_hi = self.z_range
            if range_lo != None:
                scale_lo = range_lo
            if range_hi != None:
                scale_hi = range_hi
        
        if scale_hi == scale_lo:
            scale_hi = scale_lo + 1
        self.last_limits = (scale_lo, scale_hi)
        # Transform
        data = (data-scale_lo)/(scale_hi-scale_lo)
        if clip_vals == None:
            clip_vals = (0,1)
        data[data<0] = clip_vals[0]
        data[data>1] = clip_vals[1]
        if mask_val != None and mask != None:
            data[~mask] = mask_val
        return data
    
    def clear_offset(self):
        self.z_offset = None

    def set_grab_offset(self):
        self.trigger_grab_offset = True

    def set_autostretch(self):
        self.trigger_stretch = True

    def set_mode(self, mode):
        self.mode = mode
        if mode == 'stretch':
            self.trigger_stretch = True
        
