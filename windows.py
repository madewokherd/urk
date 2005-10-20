import gtk

import ui
from conf import conf

def get_default_write(self):  
    def def_f(text, activity_type=ui.EVENT):
        if ui.windows.manager.get_active() != self:
            self.activity |= activity_type

        self.output.write(text, activity_type)
        
    return def_f
    
def get_default_transfer_text(self):
    def def_f(widget, event):
        if event.string and not self.input.is_focus():
            self.input.grab_focus()
            self.input.set_position(-1)
            self.input.event(event)
            
    return def_f

def StatusWindow(self):    
    if hasattr(self, "output"):
        parent = self.output.get_property("parent")
        if parent:
            parent.remove(self.output)
        
    else:
        self.output = ui.widgets.TextOutput(self)

    if hasattr(self, "input"):
        parent = self.input.get_property("parent")
        if parent:
            parent.remove(self.input)

    else:
        self.input = ui.widgets.TextInput(self)

    self.nick_label = ui.widgets.NickEdit(self)

    def get_title():
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server
    self.get_title = get_title

    self.focus = self.input.grab_focus
    self.write = get_default_write(self)
    self.connect("key-press-event", get_default_transfer_text(self))

    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    topbox.add(self.output)

    self.pack_start(topbox)

    botbox = gtk.HBox()
    botbox.pack_start(self.input)
    botbox.pack_end(self.nick_label, expand=False)

    self.pack_end(botbox, expand=False)

    self.show_all()
     
def QueryWindow(self):
    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title
    
    StatusWindow(self)

def ChannelWindow(self):
    if hasattr(self, "output"):
        parent = self.output.get_property("parent")
        if parent:
            parent.remove(self.output)
        
    else:
        self.output = ui.widgets.TextOutput(self)
        
    if hasattr(self, "input"):
        parent = self.input.get_property("parent")
        if parent:
            parent.remove(self.input)

    else:
        self.input = ui.widgets.TextInput(self)

    self.nicklist = ui.widgets.Nicklist(self)
    self.nick_label = ui.widgets.NickEdit(self)
    
    def set_nicklist(nicks):
        self.nicklist.userlist.clear()
        [self.nicklist.userlist.append([nick]) for nick in nicks]
    self.set_nicklist = set_nicklist

    self.focus = self.input.grab_focus
    self.write = get_default_write(self)

    self.connect("key-press-event", get_default_transfer_text(self))

    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title
    
    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    topbox.add(self.output)
    
    pane = gtk.HPaned()  
    pane.pack1(topbox, resize=True, shrink=False)
    pane.pack2(self.nicklist, resize=False, shrink=True)
    
    self.pack_start(pane)
    
    botbox = gtk.HBox()
    botbox.pack_start(self.input)
    botbox.pack_end(self.nick_label, expand=False)
    
    self.pack_end(botbox, expand=False)

    self.show_all()
