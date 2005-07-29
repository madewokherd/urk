from parse_mirc import parse_mirc

BOLD = '\x02'
UNDERLINE = '\x1F'
REVERSE = '\x16'
MIRC_COLOR = '\x03'
BERS_COLOR = '\x04'
RESET = '\x0F'

events = {}
widgets = {}

def load_theme(theme_name):
    theme_file = __import__(theme_name.strip(".py"))

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

def preText(event):
    event.done = True

    if event.network.me == event.source:
        to_write = "\x02\x04FF00FF<\x04\x02%s\x02\x04FF00FF>\x04\x02 %s" % (event.source, event.text)
    else:
        to_write = "\x02\x040000CC<\x04\x02%s\x02\x040000CC>\x04\x02 %s" % (event.source, event.text)
        
    event.window.write(to_write)
    
def preJoin(event):
    event.done = True
    
    if event.network.me == event.source:
        to_write = "\x02You\x02 joined %s" % event.target
    else:
        to_write = "\x02%s\x02 (%s) joined %s" % (event.source, event.source.address, event.target)
        
    event.window.write(to_write)
        
def postRaw(event):
    if not event.done:
        event.window.write("* %s %s" % (event.source, event.text))
    
