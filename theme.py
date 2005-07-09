import gtk

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
tags = gtk.TextTagTable()

def load_theme(theme_name):
    theme_file = __import__(theme_name.strip(".py"))
    
    # go through event types
    events.update(theme_file.format)
    
    # go through widget decoration
    widgets.update(theme_file.widgets)

    # go through tag styles
    for tag_name, style in theme_file.style.items():
        tag = gtk.TextTag(tag_name)

        for name, value in style.items():
            tag.set_property(name, value)

        tags.add(tag)
        
def apply(widget_style, widget_f):
    if widget_style in widgets:
        color = gtk.gdk.color_parse(widgets[widget_style])

        widget_f(gtk.STATE_NORMAL, color)
