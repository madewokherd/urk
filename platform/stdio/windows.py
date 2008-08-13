import sys

import irc
from conf import conf
import widgets
import events
import parse_mirc

def append(window):
    manager.add(window)

def remove(window):
    manager.remove(window)
    
    # i don't want to have to call this
    window.destroy()
    
def new(wclass, network, id):
    if network is None:
        network = irc.dummy_network
    
    w = get(wclass, network, id)
    
    if not w:
        w = wclass(network, id)
        append(w)

    return w
    
def get(windowclass, network, id):
    if network:
        id = network.norm_case(id)
        
    for w in manager:
        if (type(w), w.network, w.id) == (windowclass, network, id):
            return w
  
def get_with(wclass=None, network=None, id=None):
    if network and id:
        id = network.norm_case(id)

    for w in list(manager):
        for to_find, found in ((wclass, type(w)), (network, w.network), (id, w.id)):
            # to_find might be False but not None (if it's a DummyNetwork)
            if to_find is not None and to_find != found:
                break
        else:
            yield w
            
def get_default(network):
    window = manager.get_active()
    if window.network == network:
        return window

    # There can be only one...
    for window in get_with(network=network):
        return window

class Window(object):
    #need_parent_init = True    
    
    def mutate(self, newclass, network, id):
        isactive = self == manager.get_active()

        self.__class__ = newclass
        self.__init__(network, id)
        self.update()
        if isactive:
            self.activate()
        
    def write(self, text, activity_type=widgets.EVENT, line_ending='\n', fg=None):
        tags, text = parse_mirc.parse_mirc(text)
        sys.stdout.write('%s: %s%s' % (self.id, text, line_ending))

    def get_id(self):
        if self.network:
            return self.network.norm_case(self.rawid)
        else:
            return self.rawid
            
    def set_id(self, id):
        self.rawid = id
        self.update()

    id = property(get_id, set_id)
    
    def get_toplevel_title(self):
        return self.rawid
    
    def get_title(self):
        return self.rawid

    def get_activity(self):
        return self.__activity
    
    def set_activity(self, value):
        if value:
            self.__activity.add(value)
        else:
            self.__activity = set()
        self.update()
        
    activity = property(get_activity, set_activity)
    
    def activate(self):
        manager.set_active(self)
    
    def close(self):
        events.trigger("Close", window=self)
        remove(self)
        
    def update(self):
        manager.update(self)

    def __init__(self, network, id):
        #if self.need_parent_init:
            #make sure we don't call this an extra time when mutating
            #object.__init__(self, False)
            #self.need_parent_init = False
        
        self.network = network
        self.rawid = id
        
        self.__activity = set()
    
    def entered_text(self, text):
        for line in text.splitlines():
            if line:
                e_data = events.data(
                            window=self, network=self.network,
                            text=line, ctrl=None
                            )
                events.trigger('Input', e_data)
                
                if not e_data.done:
                    events.run(line, self, self.network)

class SimpleWindow(Window):
    pass

class StatusWindow(Window):
    def get_toplevel_title(self):
        return '%s - %s' % (self.network.me, self.get_title())

    def get_title(self):
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server

class QueryWindow(Window):
    pass

class ChannelWindow(Window):
    def __init__(self, network, id):
        Window.__init__(self, network, id)
        
        self.nicklist = widgets.Nicklist(self)

manager = widgets.UrkUITabs()

