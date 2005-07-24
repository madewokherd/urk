import gtk
import pango

def parse_mirc(string):
    start = 0
    pos = 0
    props = {}
    tag_data = []
    new_string = ''
    while pos < len(string):
        char = string[pos]
        if char == '\x02': #bold
            if start != pos:
                if props:
                    tag_data.append((props.items(), start, pos))
                start = pos
            if 'weight' in props:
                del props['weight']
            else:
                props['weight'] = pango.WEIGHT_BOLD
            pos += 1
        else:
            new_string += char
            pos += 1
    if start != pos and props:
        tag_data.append((props.items(), start, pos-1))
    return tag_data, new_string

def get_tag_table(tag_data):
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
    
    tag_data = get_tag_table(tag_data)
    
    event.window.write_with_tags(to_write, tag_data)

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
