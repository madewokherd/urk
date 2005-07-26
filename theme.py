import gtk
import pango

from parse_mirc import parse_mirc

def get_tag_data(tag_data):
    tags = []

    for props, start, end in tag_data:
        tag = gtk.TextTag()
        
        for prop, val in props:
            tag.set_property(prop, val)
        
        tags.append((tag, start, end))
    
    return tags

def __call__(event):
    if event.type in events:
        to_write = events[event.type] % event.__dict__
        
    elif "event" in events:
        to_write = events["event"] % event.__dict__
        
    else:
        to_write = " ".join(event.msg)
        
    tag_data, to_write = parse_mirc(to_write)
    
    tag_data = get_tag_data(tag_data)
    
    event.window.write(to_write, tag_data)

class Theme:
    pass
    
class default_dict(dict):
    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            return None

events = {}
widgets = {}

def load_theme(theme_name):
    theme_file = __import__(theme_name.strip(".py"))
    
    # go through event types
    events.update(theme_file.format)
    
    # go through widget decoration
    widgets.update(theme_file.widgets)
    
def font(widget_f, widget):
    if widget in widgets:
        font = pango.FontDescription(widgets[widget])

        widget_f(font)
        
def color(widget_f, widget):
    if widget in widgets:
        color = gtk.gdk.color_parse(widgets[widget])

        widget_f(gtk.STATE_NORMAL, color)
