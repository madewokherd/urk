import gtk
import pango

colors = (
  'white', 'black', '#00007F', '#009300', 
  'red', '#7F0000', '#9C009C', '#FF7F00',
  'yellow', 'green', '#009393', '#00FFFF',
  '#0000FF', '#FF00FF', '#7F7F7F', '#D2D2D2')

def get_mirc_color(number):
    return colors[int(number) % len(colors)]

def ishex(string):
    for char in string:
        if char.upper() not in '0123456789ABCDEF':
            return False
    return True

def parse_mirc(string):
    start = 0
    pos = 0
    props = {}
    tag_data = []
    new_string = ''
    while pos < len(string):
        char = string[pos]
        if char == '\x02': #bold
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            if 'weight' in props:
                del props['weight']
            else:
                props['weight'] = pango.WEIGHT_BOLD
            pos += 1
        elif char == '\x1F': #underline
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            if 'underline' in props:
                del props['underline']
            else:
                props['underline'] = True
            pos += 1
        elif char == '\x16': #reverse
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            #This isn't entirely correct, but reverse is rarely used and I'd
            # need to add extra state to really do it correctly
            if props.get('foreground') == 'white' and \
              props.get('background' == 'black'):
                del props['foreground']
                del props['background']
            else:
                props['foreground'] = 'white'
                props['background'] = 'black'
            pos += 1
        elif char == '\x03': #khaled color
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            pos += 1
            if pos < len(string) and string[pos].isdigit():
                fg = string[pos]
                pos += 1
                if pos < len(string) and string[pos].isdigit():
                    fg += string[pos]
                    pos += 1
                if fg != '99':
                    props['foreground'] = get_mirc_color(fg)
                elif 'foreground' in props:
                    del props['foreground']
                if pos+1 < len(string) and string[pos] == ',' and string[pos+1].isdigit():
                    bg = string[pos+1]
                    pos += 2
                    if pos < len(string) and string[pos].isdigit():
                        bg += string[pos]
                        pos += 1
                    if bg != '99':
                        props['background'] = get_mirc_color(bg)
                    elif 'background' in props:
                        del props['background']
            else:
                if 'foreground' in props:
                    del props['foreground']
                if 'background' in props:
                    del props['background']
        elif char == '\x04': #bersirc color
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            pos += 1
            if pos+5 < len(string) and ishex(string[pos:pos+6]):
                fg = '#'+string[pos:pos+6]
                pos += 6
                props['foreground'] = fg
                if pos+6 < len(string) and string[pos] == ',' and ishex(string[pos+1:pos+7]):
                    bg = '#'+string[pos+1:pos+7]
                    pos += 7
                    props['background'] = bg
            else:
                if 'foreground' in props:
                    del props['foreground']
                if 'background' in props:
                    del props['background']
        elif char == '\x0F': #reset formatting
            if start != len(new_string):
                if props:
                    tag_data.append((props.items(), start, len(new_string)))
                start = len(new_string)
            props.clear()
            pos += 1
        else:
            new_string += char
            pos += 1
    if start != len(new_string) and props:
        tag_data.append((props.items(), start, len(new_string)))
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
