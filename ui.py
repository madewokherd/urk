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

def quit(action=None):
    enqueue(raise_keyboard_interrupt)

menu = (
    ("FileMenu", None, "_File"),
        ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, quit),
        ("Connect", None, "_Connect", None, None, connectToArlottOrg),
    
    ("EditMenu", None, "_Edit"),
        ("Preferences", gtk.STOCK_PREFERENCES, "Pr_eferences", None, None),
    
    ("HelpMenu", None, "_Help"),
        ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about)
)

ui_info = \
"""<ui>
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
</ui>"""

class NickLabel(gtk.Label):
    def __init__(self, *args, **kwargs):
        gtk.Label.__init__(self, *args, **kwargs)

class IrcWindow(gtk.VBox):
    network = None
 
    # the all knowing print to our text window function
    def write(self, text):
        enqueue(self.write_unsafe, text)
    
    def write_unsafe(self, text):
        newline = "\n"
        
        v_buffer = self.view.get_buffer()
        
        end_rect = self.view.get_iter_location(v_buffer.get_end_iter())
        vis_rect = self.view.get_visible_rect()

        do_scroll = end_rect.y + end_rect.height <= vis_rect.y + vis_rect.height
    
        if v_buffer.get_char_count() == 0:
            newline = ""
    
        v_buffer.insert(v_buffer.get_end_iter(), newline + text)

        if do_scroll:
            scroll_to = v_buffer.create_mark("", v_buffer.get_end_iter())
            self.view.scroll_mark_onscreen(scroll_to)
    
    # we entered some text in the entry box
    def entered_text(self, entry, data=None):    
        lines = entry.get_text().split("\n")

        for line in lines:
            if line:
                self.entered_line(line)
                self.entry.history.insert(1, line)
                self.entry.history_pos = 0
        
        entry.set_text("")
    
    def entered_line(self, text):
        e_data = events.data()
        e_data.window = self
        e_data.text = text
        e_data.network = self.network
        events.trigger('Input', e_data)

    # this is our editbox   
    def bottom_section(self):
        box = gtk.HBox()
        
        self.entry = gtk.Entry()
        self.entry.connect("activate", self.entered_text)
        
        self.entry.history = [""]
        self.entry.history_pos = 0
        
        def history_explore(widget, event):
            up = gtk.gdk.keyval_from_name("Up")
            down = gtk.gdk.keyval_from_name("Down")
        
            if event.keyval in (up, down):
                # if we're going up, we go back in history
                if event.keyval == up:
                    # when we travel back in time, we need to remember
                    # where we were, so we can go back to the future
                    if self.entry.history_pos == 0 and self.entry.get_text():
                        self.entry.history.insert(1, self.entry.get_text())
                        self.entry.history_pos = 1
                
                    if self.entry.history_pos < len(self.entry.history)-1:
                        self.entry.history_pos += 1
                
                # if we're going down, we go forward in history    
                elif event.keyval == down:
                    if self.entry.history_pos:
                        self.entry.history_pos -= 1

                self.entry.set_text(self.entry.history[self.entry.history_pos])
                self.entry.set_position(-1)
                
                return True # stop other events being triggered
            
        self.entry.connect("key-press-event", history_explore)
        
        self.nick_label = NickLabel(conf.get("nick"))
        self.nick_label.set_padding(5, 0)

        box.pack_start(self.entry)
        box.pack_end(self.nick_label, expand=False)

        return box
        
    # top half of an irc window, channel window and nicklist                
    def top_section(self):
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
        
        top, bot = self.top_section(), self.bottom_section()
        
        v_buffer = self.view.get_buffer()        
        
        def focus_entry(*args):
            self.entry.set_property("has-focus", True)

        self.view.connect("focus", focus_entry, "here1")

        self.pack_start(top)
        self.pack_end(bot, expand=False)   
        self.show_all()
        
class IrcChannelWindow(IrcWindow):
    # top half of an irc window, channel window and nicklist                
    def top_section(self):
        top = IrcWindow.top_section(self)
        
        self.nicklist = gtk.TreeView()
        
        win = gtk.HPaned()
        
        win.pack1(top, resize=True)
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
                insert_candidate = self.tabs.get_nth_page(i)
                
                if insert_candidate.network == network:
                    pos = i+1
                    break
            
        self.tabs.insert_page(window, title, pos)

    def shutdown(self, *args):
        conf.set("xy", self.get_position())
        conf.set("wh", self.get_size())

    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        self.set_title("Urk")

        def destroy(*args):
            enqueue(raise_quit)
        self.connect("destroy", destroy)
        self.connect("delete_event", self.shutdown)
        
        xy = conf.get("xy") or (-1, -1)
        wh = conf.get("wh") or (500, 500)
        
        self.move(*xy)
        self.set_default_size(*wh)
        
        actions = gtk.ActionGroup("Actions")
        actions.add_actions(menu)

        ui = gtk.UIManager()
        ui.add_ui_from_string(ui_info)
        ui.insert_action_group(actions, 0)

        # create some tabs
        self.tabs = gtk.Notebook()
        self.tabs.set_property("tab-pos", gtk.POS_TOP)        
        
        self.tabs.set_border_width(10)                
        self.tabs.set_scrollable(True)
        self.tabs.set_show_border(True)

        first_window = IrcWindow("Status Window")
        first_window.type = "first_window"

        self.new_tab(first_window)
        activate(0) # status window
        
        box = gtk.VBox(False)
        box.pack_start(ui.get_widget("/MenuBar"), expand=False)
        box.pack_end(self.tabs)

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

def raise_quit():
    raise Quitting

def raise_keyboard_interrupt():
    raise KeyboardInterrupt


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
