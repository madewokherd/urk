from gi.repository import Gtk

import irc
from conf import conf
import widgets
import events

manager = widgets.UrkUITabs()

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

class Window(Gtk.VBox):
    _need_window_init = True
    
    def mutate(self, newclass, network, id):
        isactive = self == manager.get_active()

        self.__class__ = newclass
        self.__init__(network, id)
        self.update()
        if isactive:
            self.activate()
        
    def transfer_text(self, _widget, event):
        if event.string and not self.input.is_focus():
            self.input.grab_focus()
            self.input.set_position(-1)
            self.input.event(event)
        
    def write(self, text, activity_type=widgets.EVENT, line_ending='\n', fg=None):
        if manager.get_active() != self:
            self.activity = activity_type
        self.output.write(text, line_ending, fg)

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
    
    def focus(self):
        pass
    
    def activate(self):
        manager.set_active(self)
        self.focus()
    
    def close(self):
        events.trigger("Close", window=self)
        remove(self)
        
    def update(self):
        manager.update(self)

    def __init__(self, network, id):
        if self._need_window_init:
            #make sure we don't call this an extra time when mutating
            GObject.GObject.__init__(self, False)
            self._need_window_init = False
        
            self.output = widgets.TextOutput(self)
            self.buffer = self.output.get_buffer()
            
            self.input = widgets.TextInput(self)

            self.__activity = set()
        
        self.network = network
        self.rawid = id
        
    
class SimpleWindow(Window):
    def __init__(self, network, id):    
        Window.__init__(self, network, id)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        self.pack_end(self.input, False, True, 0)
        
        topbox = Gtk.ScrolledWindow()
        topbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        topbox.add(self.output)

        self.pack_end(topbox, True, True, 0)

        self.show_all()

class _ChannelStatusBase(Window):
    _need_channelstatusbase_init = True

    def __init__(self, network, id):
        Window.__init__(self, network, id)

        if self._need_channelstatusbase_init:
            self.nicklist = widgets.Nicklist(self)
            self.nick_label = widgets.NickEditor(self)

            self.focus = self.input.grab_focus
            self.connect("key-press-event", self.transfer_text)
            
            topbox = Gtk.ScrolledWindow()
            topbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            topbox.add(self.output)
            
            self.nlbox = Gtk.ScrolledWindow()
            self.nlbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)   
            self.nlbox.add(self.nicklist)

            self.nlbox.set_size_request(conf.get("ui-gtk/nicklist-width", 112), -1)

            botbox = Gtk.HBox()
            botbox.pack_start(self.input, True, True, 0)
            botbox.pack_end(self.nick_label, False, True, 0)
            
            self.pack_end(botbox, False, True, 0)
            
            pane = Gtk.HPaned()
            pane.pack1(topbox, resize=True, shrink=False)
            pane.pack2(self.nlbox, resize=False, shrink=True)
            
            self.nicklist.pos = None
     
            pane.connect("button-press-event", move_nicklist)
            pane.connect("button-release-event", drop_nicklist)
            
            self.pack_end(pane, True, True, 0)

            self.show_all()

            self._need_channelstatusbase_init = False

class StatusWindow(_ChannelStatusBase):
    def get_toplevel_title(self):
        return '%s - %s' % (self.network.me, self.get_title())

    def get_title(self):
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server

    def __init__(self, network, id):
        _ChannelStatusBase.__init__(self, network, id)

        self.nlbox.hide()

class QueryWindow(Window):
    def __init__(self, network, id):    
        Window.__init__(self, network, id)

        self.nick_label = widgets.NickEditor(self)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        botbox = Gtk.HBox()
        botbox.pack_start(self.input, True, True, 0)
        botbox.pack_end(self.nick_label, False, True, 0)

        self.pack_end(botbox, False, True, 0)
        
        topbox = Gtk.ScrolledWindow()
        topbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        topbox.add(self.output)

        self.pack_end(topbox, True, True, 0)

        self.show_all()

def move_nicklist(paned, event):
    paned._moving = (
        event.type == Gdk._2BUTTON_PRESS,
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

class ChannelWindow(_ChannelStatusBase):
    def __init__(self, network, id):
        _ChannelStatusBase.__init__(self, network, id)

        self.nlbox.show()

