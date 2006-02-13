import gtk
import pango

import ui
from conf import conf

def get_default_write(self):  
    def def_f(text, activity_type=ui.EVENT, line_ending='\n'):
        if ui.windows.manager.get_active() != self:
            self.activity = max(self.activity, activity_type)

        self.output.write(text, activity_type, line_ending)
        
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
        if self.output.parent:
            self.output.parent.remove(self.output)
        
    else:
        self.output = ui.widgets.TextOutput(self)
        
    if hasattr(self, "input"):
        if self.input.parent:
            self.input.parent.remove(self.input)

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

    botbox = gtk.HBox()
    botbox.pack_start(self.input)
    botbox.pack_end(self.nick_label, expand=False)

    self.pack_end(botbox, expand=False)
    
    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    topbox.add(self.output)

    self.pack_end(topbox)

    self.show_all()
     
def QueryWindow(self):
    StatusWindow(self)
    
    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title

def ChannelWindow(self):
    if hasattr(self, "output"):
        if self.output.parent:
            self.output.parent.remove(self.output)
        
    else:
        self.output = ui.widgets.TextOutput(self)
        
    if hasattr(self, "input"):
        if self.input.parent:
            self.input.parent.remove(self.input)

    else:
        self.input = ui.widgets.TextInput(self)

    self.nicklist = ui.widgets.Nicklist(self)
    self.nick_label = ui.widgets.NickEdit(self)

    self.focus = self.input.grab_focus
    self.write = get_default_write(self)

    self.connect("key-press-event", get_default_transfer_text(self))

    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title
    
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
    
    nl_pos = [None]    
    def move_nicklist(paned, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            nl_pos[0] = paned.get_position()
    
    def drop_nicklist(paned, event):
        width = paned.allocation.width
        pos = paned.get_position()

        if pos == nl_pos[0]:
            if width - pos <= 10:
                conf_nicklist = conf.get("ui-gtk/nicklist-width", 200)

                if conf_nicklist <= 10:
                    paned.set_position(width - 200)
                else:
                    paned.set_position(width - conf_nicklist)
            else:
                paned.set_position(width)
                
        else:
            conf["ui-gtk/nicklist-width"] = width - pos - 6
            
        nl_pos[0] = None
        
    pane.connect("button-press-event", move_nicklist)
    pane.connect("button-release-event", drop_nicklist)
    
    self.pack_end(pane)

    self.show_all()
