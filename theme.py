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
