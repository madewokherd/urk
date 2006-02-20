import gtk

import irc
from conf import conf
import widgets
import events

def append(window):
    manager.add(window)

def remove(window):
    manager.remove(window)

def new(wclass, network, id):
    w = get(wclass, network, id)
    
    if not w:
        w = wclass(network or irc.Network(), id)
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
        for to_find, found in zip((wclass, network, id), (type(w), w.network, w.id)):
            if to_find and to_find != found:
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

class Window(gtk.VBox):
    def mutate(self, newclass, network, id):
        self.hide()
    
        for child in self.get_children():
            self.remove(child)

        self.__class__ = newclass
        self.__init__(network, id)
        self.update()
        
    def transfer_text(self, _widget, event):
        if event.string and not self.input.is_focus():
            self.input.grab_focus()
            self.input.set_position(-1)
            self.input.event(event)
        
    def write(self, text, activity_type=widgets.EVENT, line_ending='\n'):
        if manager.get_active() != self:
            self.activity = max(self.activity, activity_type)

        self.output.write(text, line_ending)

    def get_id(self):
        if self.network:
            return self.network.norm_case(self.__id)
        else:
            return self.__id
            
    def set_id(self, id):
        self.__id = id
        self.update()

    id = property(get_id, set_id)
    
    def get_title(self):
        return self.__id

    def __get_title(self):
        return self.get_title()
    
    def set_title(self, title):
        self.update()
        
    title = property(__get_title, set_title)

    def get_activity(self):
        return self.__activity
    
    def set_activity(self, value):
        self.__activity = value
        self.update()
        
    activity = property(get_activity, set_activity)
    
    def focus(self):
        pass
    
    def activate(self):
        manager.set_active(self)
        self.focus()
    
    def close(self):
        events.trigger("Close", self)
        remove(self)
        
    def update(self):
        manager.update(self)

    def __init__(self, network, id):
        gtk.VBox.__init__(self, False)
        
        if hasattr(self, "output"):
            if self.output.parent:
                self.output.parent.remove(self.output)
            
        else:
            self.output = widgets.TextOutput(self)
            
        if hasattr(self, "input"):
            if self.input.parent:
                self.input.parent.remove(self.input)

        else:
            self.input = widgets.TextInput(self)
        
        self.network = network
        self.__id = id
        
        self.__activity = 0

class StatusWindow(Window):
    def get_title(self):
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server

    def __init__(self, network, id):    
        Window.__init__(self, network, id)

        self.nick_label = widgets.NickEditor(self)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        botbox = gtk.HBox()
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)

        self.pack_end(botbox, expand=False)
        
        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)

        self.pack_end(topbox)

        self.show_all()
     
class QueryWindow(Window):
    def __init__(self, network, id):    
        Window.__init__(self, network, id)

        self.nick_label = widgets.NickEditor(self)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        botbox = gtk.HBox()
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)

        self.pack_end(botbox, expand=False)
        
        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)

        self.pack_end(topbox)

        self.show_all()

def move_nicklist(paned, event):
    paned._moving = (
        event.type == gtk.gdk._2BUTTON_PRESS,
        paned.get_position()
        )
        
def drop_nicklist(paned, event):
    width = paned.allocation.width
    pos = paned.get_position()
    
    double_click, nicklist_pos = paned._moving

    if double_click:
        # if we're "hidden", then we want to unhide
        if width - pos <= 10:
            # get the normal nicklist width
            conf_nicklist = conf.get("ui-gtk/nicklist-width", 200)

            # if the normal nicklist width is "hidden", then ignore it
            if conf_nicklist <= 10:
                paned.set_position(width - 200)
            else:
                paned.set_position(width - conf_nicklist)

        # else we hide
        else:
            paned.set_position(width)
        
    else:    
        if pos != nicklist_pos:
            conf["ui-gtk/nicklist-width"] = width - pos - 6

class ChannelWindow(Window):
    def __init__(self, network, id):
        Window.__init__(self, network, id)

        self.nicklist = widgets.Nicklist(self)
        self.nick_label = widgets.NickEditor(self)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)
        
        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)
        
        nlbox = gtk.ScrolledWindow()
        nlbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)   
        nlbox.add(self.nicklist)

        nlbox.set_size_request(conf.get("ui-gtk/nicklist-width", 0), -1)

        botbox = gtk.HBox()
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)
        
        self.pack_end(botbox, expand=False)
        
        pane = gtk.HPaned()
        pane.pack1(topbox, resize=True, shrink=False)
        pane.pack2(nlbox, resize=False, shrink=True)
        
        self.nicklist.pos = None
 
        pane.connect("button-press-event", move_nicklist)
        pane.connect("button-release-event", drop_nicklist)
        
        self.pack_end(pane)

        self.show_all()
