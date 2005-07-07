import time

import pygtk
import gtk
import gobject

import conf
import events

modifiers = (gtk.gdk.CONTROL_MASK, gtk.gdk.MOD1_MASK,
                gtk.gdk.MOD2_MASK, gtk.gdk.MOD3_MASK,
                gtk.gdk.MOD4_MASK, gtk.gdk.MOD5_MASK)
                        
MOD_MASK = 0
for m in modifiers:
    MOD_MASK |= m   

# FIXME: get rid of this
def print_args(*args):
    print args

def connectToArlottOrg(widget):
    events.trigger("ConnectArlottOrg")
    
def urk_about(action):
    about = gtk.AboutDialog()
    
    about.set_name("Urk")
    about.set_version("8")
    about.set_copyright("Yes, 2004")
    about.set_comments("Comments")
    about.set_license("Gee Pee Ell")
    about.set_website("http://urk.sf.net")
    about.set_authors(__import__("random").sample(["Marc","MadEwokHerd"], 2))
    
    about.show_all()
    
def close_tab(action):
    ui.tabs.remove_page(ui.tabs.get_current_page())
    
def get_menu(ui):
    return (
        ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, ui.shutdown),
            ("Connect", None, "_Connect", None, None, connectToArlottOrg),
        
        ("EditMenu", None, "_Edit"),
            ("Preferences", gtk.STOCK_PREFERENCES, "Pr_eferences", None, None),
        
        ("HelpMenu", None, "_Help"),
            ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about),
            
        ("CloseTab", None, "_Close Tab", None, None, close_tab)
    )

ui_info = \
"""
<ui>
 <menubar name="MenuBar">
  <menu action="FileMenu">
   <menuitem action="Connect"/>
   <menuitem action="Quit"/>
  </menu>
  
  <menu action="EditMenu">
   <menuitem action="Preferences"/>
  </menu>
  
  <menu action="HelpMenu">
   <menuitem action="About"/>
  </menu>
 </menubar>
 
 <popup name="TabPopup">
   <menuitem action="CloseTab"/>
 </popup>
</ui>
"""

class NickLabel(gtk.Label):
    pass
    #def __init__(self, *args, **kwargs):
    #    gtk.Label.__init__(self, *args, **kwargs)

class IrcWindow(gtk.VBox):
    network = None
 
    # the all knowing print to our text window function
    def write(self, text):
        enqueue(self.write_unsafe, text)
    
    def write_unsafe(self, text):
        buffer = self.view.get_buffer()
        end = buffer.get_end_iter()
        
        end_rect = self.view.get_iter_location(end)
        vis_rect = self.view.get_visible_rect()

        do_scroll = end_rect.y + end_rect.height <= vis_rect.y + vis_rect.height
    
        if buffer.get_char_count():
            newline = "\n"
        else:
            newline = ""
    
        buffer.insert(end, newline + text)

        if do_scroll:
            self.view.scroll_mark_onscreen(buffer.create_mark("", end))
    
    # we entered some text in the entry box
    def entered_text(self, entry, data=None):    
        lines = entry.get_text().split("\n")

        for line in lines:
            if line:
                self.entered_line(line)
                self.entry.history.insert(1, line)
                self.entry.history_i = 0
        
        entry.set_text("")
    
    def entered_line(self, text):
        e_data = events.data()
        e_data.window = self
        e_data.text = text
        e_data.network = self.network
        events.trigger('Input', e_data)

    # this is our text entry widget
    def entry_box(self):
        self.entry = gtk.Entry()
        self.entry.connect("activate", self.entered_text)
        
        self.entry.history = [""]
        self.entry.history_i = 0
        
        def history_explore(widget, event):
            up = gtk.gdk.keyval_from_name("Up")
            down = gtk.gdk.keyval_from_name("Down")
        
            if event.keyval in (up, down):
                # we go forward in history
                di = -1
                    
                if event.keyval == up:
                    # we go back in history
                    di = 1
                    
                    # when we travel back in time, we need to remember
                    # where we were, so we can go back to the future
                    if self.entry.history_i == 0 and self.entry.get_text():
                        self.entry.history.insert(1, self.entry.get_text())
                        self.entry.history_i = 1

                if self.entry.history_i + di in range(len(self.entry.history)):
                    self.entry.history_i += di

                self.entry.set_text(self.entry.history[self.entry.history_i])
                self.entry.set_position(-1)
                
                return True # stop other events being triggered
            
        self.entry.connect("key-press-event", history_explore)
        
        self.nick_label = NickLabel(conf.get("nick"))
        self.nick_label.set_padding(5, 0)

        box = gtk.HBox()
        box.pack_start(self.entry)
        box.pack_end(self.nick_label, expand=False)

        return box
        
    # non-channel channel window, no nicklist         
    def chat_view(self):
        self.view = gtk.TextView()
        self.view.set_wrap_mode(gtk.WRAP_WORD)
        self.view.set_editable(False)
        self.view.set_cursor_visible(False)

        def transfer_text(widget, event):
            modifiers_on = event.state & MOD_MASK

            if event.string and not modifiers_on:
                self.entry.grab_focus()
                self.entry.insert_text(event.string, -1)
                self.entry.set_position(-1)
        
        self.view.connect("key-press-event", transfer_text)

        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        win.set_border_width(2)
        win.add(self.view)

        return win

    def __init__(self, title=""):
        gtk.VBox.__init__(self, False)
        
        self.title = title

        self.pack_start(self.chat_view())
        self.pack_end(self.entry_box() , expand=False)
  
        self.show_all()
        
class IrcChannelWindow(IrcWindow):
    # channel window and nicklist               
    def chat_view(self):
        self.nicklist = gtk.TreeView()
        
        win = gtk.HPaned()
        win.pack1(IrcWindow.chat_view(self), resize=True)
        win.pack2(self.nicklist, resize=False)
        
        return win

class IrcUI(gtk.Window):
    def new_tab(self, window, network=None):
        def focus_entry(*args):
            window.entry.grab_focus()
            
        window.connect("focus", focus_entry)
    
        enqueue(self.new_tab_unsafe, window, network)

    def new_tab_unsafe(self, window, network=None):
        title = gtk.Label(window.title)
        
        window.network = network
        
        pos = self.tabs.get_n_pages()
        
        if network:
            for i in reversed(xrange(pos)):
                if self.tabs.get_nth_page(i).network == network:
                    pos = i+1
                    break
            
        self.tabs.insert_page(window, title, pos)

    def shutdown(self, *args):
        conf.set("xy", self.get_position())
        conf.set("wh", self.get_size())
        
        enqueue(quit)
        
    def make_notebook(self, ui):
        self.tabs = gtk.Notebook()
        self.tabs.set_property("tab-pos", gtk.POS_TOP)
        self.tabs.set_border_width(10)          
        self.tabs.set_scrollable(True)
        self.tabs.set_show_border(True)

        first_window = IrcWindow("Status Window")
        first_window.type = "first_window"

        self.new_tab(first_window)
        activate(0) # first_window
        
        self.new_tab(IrcWindow("Blah"))
        
        def tab_popup(widget, event):
            if event.button == 3: # right click
                ui.get_widget("/TabPopup").popup(None, None, None, event.button, event.time)
                    
        self.tabs.connect("button-press-event", tab_popup)

    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        self.set_title("Urk")
        
        # layout
        xy = conf.get("xy") or (-1, -1)
        wh = conf.get("wh") or (500, 500)
        
        self.move(*xy)
        self.set_default_size(*wh)
        
        # set up actions        
        actions = gtk.ActionGroup("Urk")
        actions.add_actions(get_menu(self))

        ui = gtk.UIManager()
        ui.add_ui_from_string(ui_info)
        ui.insert_action_group(actions, 0)
        
        self.make_notebook(ui)

        box = gtk.VBox(False)
        box.pack_start(ui.get_widget("/MenuBar"), expand=False)
        box.pack_end(self.tabs)
        
        self.connect("delete_event", self.shutdown)

        self.add(box)
        self.show_all()
        
def activate(widget):
    # if this is an actual widget, then we want its tab number
    if not isinstance(widget, int):
        widget = ui.tabs.page_num(widget)
        
    def to_activate():
        ui.tabs.set_current_page(widget)
        ui.tabs.get_nth_page(widget).entry.grab_focus() 
    enqueue(to_activate)

def get_window(target, src_event=None, src_name=''):
    if target.window:
        return target.window
    else:
        e_data = events.data()
        e_data.src_event = src_event
        e_data.src_name = src_name
        e_data.target = target
        e_data.window = None
        events.trigger('NewWindow', e_data)
        return e_data.window

queue = []
def enqueue(f, *args, **kwargs):
    queue.append((f, args, kwargs))

class Quitting(Exception):
    pass

def quit():
    raise Quitting

ui = IrcUI()
new_tab = ui.new_tab
tabs = ui.tabs

def start():
    try:
        while 1:
            gtk.main_iteration(block=False)
            while queue:
                f, args, kwargs = queue.pop(0)
                f(*args,**kwargs)
            time.sleep(.001)
    except KeyboardInterrupt:
        ui.shutdown()
    except Quitting:
        pass
