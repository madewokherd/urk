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

def StatusWindow(self, output=None, input=None):
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

    self.output = output or ui.widgets.TextOutput(self)

    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    topbox.add(self.output)

    self.pack_start(topbox)
    
    self.input = input or ui.widgets.TextInput(self)
    self.nick_label = ui.widgets.NickEdit(self)

    botbox = gtk.HBox()
    botbox.pack_start(self.input)
    botbox.pack_end(self.nick_label, expand=False)

    self.pack_end(botbox, expand=False)

    self.show_all()
    
    return self
     
def QueryWindow(self, output=None, input=None):
    StatusWindow(self)

    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title
    
    return self

def ChannelWindow(self, output=None, input=None):
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

    self.output = output or ui.widgets.TextOutput(self)
    self.nicklist = ui.widgets.Nicklist(self)

    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    topbox.add(self.output)
    
    pane = gtk.HPaned()
    pane.pack1(topbox, resize=True, shrink=False)
    pane.pack2(self.nicklist, resize=False, shrink=True)

    def set_pane_pos():
        pane.set_position(
            pane.get_property("max-position") - (conf.get("ui-gtk/nicklist-width") or 0)
            )
    ui.register_idle(set_pane_pos)

    def connect_save():
        def save_nicklist_width(pane, event):
            conf.set(
                "ui-gtk/nicklist-width", 
                pane.get_property("max-position") - pane.get_position()
                )
    
        pane.connect("size-request", save_nicklist_width)
    ui.register_idle(connect_save)
    
    self.pack_start(pane)
    
    self.input = input or ui.widgets.TextInput(self)
    self.nick_label = ui.widgets.NickEdit(self)

    botbox = gtk.HBox()
    botbox.pack_start(self.input)
    botbox.pack_end(self.nick_label, expand=False)
    
    self.pack_end(botbox, expand=False)

    self.show_all()