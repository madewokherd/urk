import time

import gtk
import pango

import conf
import events
import parse_mirc
          
MOD_MASK = 0
for m in (gtk.gdk.CONTROL_MASK, gtk.gdk.MOD1_MASK, gtk.gdk.MOD3_MASK,
             gtk.gdk.MOD4_MASK, gtk.gdk.MOD5_MASK):
    MOD_MASK |= m   

# FIXME: get rid of this
def print_args(*args):
    print args

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
    
def get_tab_actions(page_num):
    def close_tab(action):
        events.trigger("Close", tabs.get_nth_page(page_num))
        tabs.remove_page(page_num)
        
    to_add = (
        ("CloseTab", gtk.STOCK_CLOSE, "_Close Tab", None, None, close_tab),
        )
        
    tab_actions = gtk.ActionGroup("Tab")
    tab_actions.add_actions(to_add)
    
    return tab_actions
    
def get_urk_actions(ui):
    def connectToArlottOrg(widget):
        events.trigger("ConnectArlottOrg")

    to_add = (
        ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, ui.shutdown),
            ("Connect", None, "_Connect", None, None, connectToArlottOrg),
        
        ("EditMenu", None, "_Edit"),
            ("Preferences", gtk.STOCK_PREFERENCES, "Pr_eferences", None, None),
        
        ("HelpMenu", None, "_Help"),
            ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about)
        )
    
    urk_actions = gtk.ActionGroup("Urk")   
    urk_actions.add_actions(to_add)
    
    return urk_actions

class NickLabel(gtk.EventBox):
    def __init__(self, *args, **kwargs):
        self.label = gtk.Label(*args, **kwargs)
        self.label.set_padding(5, 0)
        
        gtk.EventBox.__init__(self)
        self.add(self.label)
        
        #self.connect("button-press-event", lambda *a: None)

class IrcWindow(gtk.VBox):
    network = None
    
    # the unknowing print weird things to our text window function
    def write(self, text):   
        def write_unsafe(view, text, tag_data):
            buffer = view.get_buffer()
            end = buffer.get_end_iter()
            
            end_rect = view.get_iter_location(end)
            vis_rect = view.get_visible_rect()

            do_scroll = end_rect.y + end_rect.height <= vis_rect.y + vis_rect.height
            
            char_count = buffer.get_char_count()

            buffer.insert(end, text + "\n")
            
            tag_table = buffer.get_tag_table()

            for props, start, end in tag_data:
                start = buffer.get_iter_at_offset(start + char_count)
                end = buffer.get_iter_at_offset(end + char_count)
            
                tag = gtk.TextTag()
                
                for prop, val in props:
                    if val == parse_mirc.BOLD:
                        val = pango.WEIGHT_BOLD
                    elif val == parse_mirc.UNDERLINE:
                        val = pango.UNDERLINE_SINGLE

                    tag.set_property(prop, val)

                tag_table.add(tag)
                buffer.apply_tag(tag, start, end)

            if do_scroll:
                view.scroll_mark_onscreen(buffer.create_mark("", end))
                
        tag_data, text = parse_mirc.parse_mirc(text)
        
        enqueue(write_unsafe, self.view, text, tag_data)
    
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
        
        cv, eb = self.chat_view(), self.entry_box()

        self.pack_start(cv)
        self.pack_end(eb, expand=False)
  
        self.show_all()
        
class IrcChannelWindow(IrcWindow):
    # channel window and nicklist               
    def chat_view(self):
        self.nicklist = gtk.TreeView()
        
        win = gtk.HPaned()
        win.pack1(IrcWindow.chat_view(self), resize=True)
        win.pack2(self.nicklist, resize=False)
        
        return win
        
class IrcTabs(gtk.Notebook):
    def __init__(self):
        gtk.Notebook.__init__(self)
        
        self.set_property("tab-pos", gtk.POS_TOP)
        self.set_border_width(10)          
        self.set_scrollable(True)
        self.set_show_border(True)
    
    # FIXME: remove this when pygtk2.8 comes around
    def __iter__(self):
        return iter(self.get_children())
        
class IrcUI(gtk.Window):
    def shutdown(self, *args):
        conf.set("xy", self.get_position())
        conf.set("wh", self.get_size())
        
        enqueue(quit)

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
        
        #self.add_accel_group(ui_manager.get_accel_group())
        ui_manager.add_ui_from_file("ui.xml")
        ui_manager.insert_action_group(get_urk_actions(self), 0)
        
        menu = ui_manager.get_widget("/MenuBar")

        # widgets
        box = gtk.VBox(False)
        box.pack_start(menu, expand=False)
        box.pack_end(tabs)
        
        self.connect("delete_event", self.shutdown)

        self.add(box)
        self.show_all()
        
# Add a tab label with this window's title
def add_tab_label(window):
    def tab_popup(widget, event):
        if event.button == 3: # right click
            page_num = tabs.page_num(widget.child_window)
            
            # add some tab UI                
            tab_id = ui_manager.add_ui_from_file("tabui.xml")
            ui_manager.insert_action_group(get_tab_actions(page_num), 0)

            tab_menu = ui_manager.get_widget("/TabPopup")
            
            # remove the tab UI, so we can recompute it later
            def remove_tab_ui(action):
                ui_manager.remove_ui(tab_id)
            tab_menu.connect("deactivate", remove_tab_ui)

            tab_menu.popup(None, None, None, event.button, event.time)

    label = gtk.EventBox()        
    label.add(gtk.Label(window.title))
    label.child_window = window
    label.connect("button-press-event", tab_popup)
    label.show_all()

    tabs.set_tab_label(window, label)

# Make a new tab with a window widget, optionally associate it with a network        
def new_tab(window, network=None):
    window.network = network

    def new_tab_unsafe():
        def focus_entry(*args):
            window.entry.grab_focus()
        window.connect("focus", focus_entry)
    
        pos = tabs.get_n_pages()
        
        if network:
            for i in reversed(xrange(pos)):
                if tabs.get_nth_page(i).network == network:
                    pos = i+1
                    break
    
        tabs.insert_page(window, None, pos)
        add_tab_label(window)
    
    enqueue(new_tab_unsafe)

# Select the page with the given window or with the given tab position
def activate(window):
    def to_activate(window):
        # if this is an actual window, then we want its tab number
        if not isinstance(window, int):
            window = tabs.page_num(window)
    
        tabs.set_current_page(window)
        tabs.get_nth_page(window).entry.grab_focus()

    enqueue(to_activate, window)

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

# UI manager to use throughout   
ui_manager = gtk.UIManager()
    
# build our tab widget
tabs = IrcTabs()

# build our overall UI
ui = IrcUI()

def start():
    first_window = IrcWindow("Status Window")
    first_window.type = "first_window"

    new_tab(first_window)
    activate(first_window)
    
    try:
        while 1:
            gtk.main_iteration(block=False)
            #FIXME: We should be using an idle timer for this
            while queue:
                f, args, kwargs = queue.pop(0)
                f(*args,**kwargs)
            time.sleep(.001)
    except KeyboardInterrupt:
        ui.shutdown()
    except Quitting:
        pass
