import gtk

import ui
import conf

def get_default_focus(self):
    def def_f():
        self.input.grab_focus()
        
    return def_f

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
    def get_title():
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server
    self.get_title = get_title

    self.focus = get_default_focus(self)
    self.write = get_default_write(self)
    self.connect("key-press-event", get_default_transfer_text(self))

    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    
    if hasattr(self, "output"):
        parent = self.output.get_property("parent")
        if parent:
            parent.remove(self.output)
        
    else:
        self.output = ui.widgets.TextOutput(self)

    topbox.add(self.output)
    
    self.pack_start(topbox)
    
    botbox = gtk.HBox()
    
    if hasattr(self, "input"):
        parent = self.input.get_property("parent")
        if parent:
            parent.remove(self.input)

    else:
        self.input = ui.widgets.TextInput(self)
    
    botbox.pack_start(self.input)

    self.nick_label = ui.widgets.NickEdit(self)

    botbox.pack_end(self.nick_label, expand=False)

    self.pack_end(botbox, expand=False)

    self.show_all()
     
def QueryWindow(self):
    StatusWindow(self)

    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title

def ChannelWindow(self):
    self.focus = get_default_focus(self)
    self.write = get_default_write(self)

    self.connect("key-press-event", get_default_transfer_text(self))

    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title

    def set_nicklist(nicks):
        self.nicklist.userlist.clear()
        
        for nick in nicks:
            self.nicklist.userlist.append([nick])
    self.set_nicklist = set_nicklist
    
    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    if hasattr(self, "output"):
        parent = self.output.get_property("parent")
        if parent:
            parent.remove(self.output)
        
    else:
        self.output = ui.widgets.TextOutput(self)
    
    topbox.add(self.output)
    
    pane = gtk.HPaned()
    pane.pack1(topbox, resize=True, shrink=False)
    
    self.nicklist = ui.widgets.Nicklist(self)
    pane.pack2(self.nicklist, resize=False, shrink=True)

    def setup_pane():
        pane.set_position(
            pane.get_property("max-position") - (conf.get("ui-gtk/nicklist-width") or 0)
            )
    
        def save_nicklist_width(pane, event):
            conf.set(
                "ui-gtk/nicklist-width", 
                pane.get_property("max-position") - pane.get_position()
                )

        pane.connect_after("size-allocate", save_nicklist_width)
    ui.register_idle(setup_pane)
    
    self.pack_start(pane)

    botbox = gtk.HBox()
    
    if hasattr(self, "input"):
        parent = self.input.get_property("parent")
        if parent:
            parent.remove(self.input)

    else:
        self.input = ui.widgets.TextInput(self)
    
    botbox.pack_start(self.input)
        
    self.nick_label = ui.widgets.NickEdit(self)

    botbox.pack_end(self.nick_label, expand=False)
    
    self.pack_end(botbox, expand=False)

    self.show_all()
