import codecs

from conf import conf
import events
import urk
import windows

# Window activity Constants
HILIT = 'h'
TEXT ='t'
EVENT = 'e'

# This holds all tags for all windows ever

#FIXME: MEH hates dictionaries, they remind him of the bad words
styles = {}

def style_me(widget, style):
    widget.set_style(styles.get(style))

def set_style(widget_name, style):
    styles[widget_name] = style

class Nicklist(object):
    def __getitem__(self, pos):
        return self.items[pos][0]
        
    def __setitem__(self, pos, name_markup):
        realname, markedupname, sortkey = name_markup
    
        self.items[pos] = realname, markedupname, sortkey

    def __len__(self):
        return len(self.items)
    
    def index(self, item):
        for i, x in enumerate(self):
            if x == item:
                return i
                
        return -1
        
    def append(self, realname, markedupname, sortkey):
        self.items.append((realname, markedupname, sortkey))
 
    def insert(self, pos, realname, markedupname, sortkey):
        self.items.insert(pos, (realname, markedupname, sortkey))
        
    def replace(self, names):
        self.items[:] = names

    def remove(self, realname):
        self.items.remove(realname)
    
    def clear(self):
        self.items[:] = []
        
    def __iter__(self):
        return (x[0] for x in self.items)

    def __init__(self, window):
        self.win = window
        
        self.items = []

class UrkUITabs(object):
    def get_active(self):
        if self.tabs:
            return self.tabs[0]
        else:
            return None
    
    def set_title(self, title=None):
        pass

    def __iter__(self):
        return iter(self.tabs)
    
    def __len__(self):
        return self.tabs.get_n_pages()
    
    def exit(self, *args):
        events.trigger("Exit")
        self.quitted = True
        
    def set_active(self, window):
        self.tabs.remove(window)
        self.tabs.insert(0, window)
        events.trigger("Active", window=window)
        
    def add(self, window):
        self.tabs.append(window)
        if len(self.tabs) == 1:
            events.trigger("Active", window=window)
        
    def remove(self, window):
        trigger_active = self.get_active() == window
        self.tabs.remove(window)
        if trigger_active:
            events.trigger("Active", window=self.get_active())
        
    def update(self, window):
        if self.get_active() == window:
            self.set_title()
    
    def __init__(self):
        self.tabs = []
        self.quitted = False

