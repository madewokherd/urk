from parse_mirc import parse_mirc

def __call__(event):
    own = str(event.source) == event.network.me

    if own and event.type in ownevents:
        to_write = ownevents[event.type] % event.__dict__
    
    elif event.type in events:
        to_write = events[event.type] % event.__dict__
        
    elif own and "event" in ownevents:
        to_write = ownevents["event"] % event.__dict__
    
    elif "event" in events:
        to_write = events["event"] % event.__dict__
        
    else:
        to_write = " ".join(event.msg)

    event.window.write(to_write)

class Theme:
    pass
    
class default_dict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            return None

events = {}
ownevents = {}

widgets = {}

def load_theme(theme_name):
    theme_file = __import__(theme_name.strip(".py"))
    
    # go through own event types
    ownevents.update(theme_file.ownformat)
    
    # go through event types
    events.update(theme_file.format)
    
    # go through widget decoration
    widgets.update(theme_file.widgets)
    
def font(widget_f, widget):
    import pango

    if widget in widgets:
        font = pango.FontDescription(widgets[widget])

        widget_f(font)
        
def color(widget_f, widget):
    import gtk

    if widget in widgets:
        color = gtk.gdk.color_parse(widgets[widget])

        widget_f(gtk.STATE_NORMAL, color)
