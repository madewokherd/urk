import gtk
import pango
import gtksourceview

import ui
from conf import conf

def get_default_write(self):  
    def def_f(text, activity_type=ui.EVENT):
        if ui.windows.manager.get_active() != self:
            self.activity = max(self.activity, activity_type)

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
    StatusWindow(self)
    
    def get_title():
        return ui.Window.get_title(self)
    self.get_title = get_title

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
    nlbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)   
    nlbox.add(self.nicklist.view)
    
    nlbox.set_size_request(conf["ui-gtk/nicklist-width"] or 0, -1)

    def save_nicklist_width(w, rectangle):
        conf["ui-gtk/nicklist-width"] = rectangle.width
    nlbox.connect("size-allocate", save_nicklist_width)
    
    pane = gtk.HPaned()  
    pane.pack1(topbox, resize=True, shrink=False)
    pane.pack2(nlbox, resize=False, shrink=True)
    
    self.pack_start(pane)
    
    botbox = gtk.HBox()
    botbox.pack_start(self.input)
    botbox.pack_end(self.nick_label, expand=False)
    
    self.pack_end(botbox, expand=False)

    self.show_all()
    
def ScriptWindow(self):    
    self.output = gtksourceview.SourceView(gtksourceview.SourceBuffer())
    
    self.output.set_auto_indent(True)
    self.output.set_show_line_numbers(True)
    self.output.set_insert_spaces_instead_of_tabs(True)
    self.output.set_show_margin(True)
    self.output.set_margin(80)
    
    buffer = self.output.get_buffer()
    language = gtksourceview.SourceLanguagesManager(). \
                    get_language_from_mime_type('text/x-python')
    
    buffer.set_language(language)
    
    buffer.set_check_brackets(True)
    buffer.set_highlight(True)

    self.focus = self.output.grab_focus
    
    def write(*args):
        pass
    self.write = write

    topbox = gtk.ScrolledWindow()
    topbox.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    topbox.add(self.output)

    self.pack_start(topbox)

    self.show_all()
