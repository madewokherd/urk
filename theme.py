import gtk

class Theme:
    pass
    
tags = gtk.TextTagTable()
events = {}

def load_theme(theme_name):
    theme_file = __import__(theme_name.strip(".py"))
    
    # go through event types
    events.update(theme_file.format)

    # go through tag styles
    for tag_name, style in theme_file.style.items():
        tag = gtk.TextTag(tag_name)

        for name, value in style.items():
            tag.set_property(name, value)

        tags.add(tag)
