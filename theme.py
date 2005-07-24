import gtk

def __call__(event):
    if event.type in events:
        event.window.write(events[event.type] % event.__dict__)
        
    elif "event" in events:
        event.window.write(events["event"] % event.__dict__)
        
    else:
        event.window.write(" ".join(event.msg))

class Theme:
    pass
    
class default_dict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            return None

events = {}
widgets = default_dict()

def load_theme(theme_name):
    theme_file = __import__(theme_name.strip(".py"))
    
    # go through event types
    events.update(theme_file.format)
    
    # go through widget decoration
    widgets.update(theme_file.widgets)
        
def color(widget_color, widget_f):
    color = gtk.gdk.color_parse(widget_color)

    widget_f(gtk.STATE_NORMAL, color)
