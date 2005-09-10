import os
import sys #only needed for the stupid workaround

import gobject
import gtk
#stupid workaround
if sys.path[0] == sys.path[3]:
    sys.path.pop(0)
import pango

import widgets
import irc
import conf
import events
import parse_mirc
import __main__ as urk

# IO Type Constants
IO_IN = gobject.IO_IN
IO_OUT = gobject.IO_OUT
IO_PRI = gobject.IO_PRI
IO_ERR = gobject.IO_ERR
IO_HUP = gobject.IO_HUP

# Priority Constants
PRIORITY_HIGH = gobject.PRIORITY_HIGH
PRIORITY_DEFAULT = gobject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = gobject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = gobject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = gobject.PRIORITY_LOW

def register_io(f, fd, condition, priority=PRIORITY_DEFAULT_IDLE, *args, **kwargs):
    def callback(source, cb_condition):
        return f(*args, **kwargs)
    return gobject.io_add_watch(fd, condition, callback, priority=priority)

def register_idle(f, priority=PRIORITY_DEFAULT_IDLE, *args, **kwargs):
    def callback():
        return f(*args, **kwargs)
    return gobject.idle_add(callback, priority=priority)

def register_timer(time, f, priority=PRIORITY_DEFAULT_IDLE, *args, **kwargs):
    def callback():
        return f(*args, **kwargs)
    return gobject.timeout_add(time, callback, priority=priority)

def unregister(tag):
    gobject.source_remove(tag)
    
set_style = widgets.set_style

# Window activity Constants
HILIT = widgets.HILIT
TEXT = widgets.TEXT
EVENT = widgets.EVENT

def urk_about(action):
    import __main__
    
    about = gtk.AboutDialog()
    
    about.set_name(__main__.name+" (GTK+ Frontend)")
    about.set_version(".".join(str(x) for x in __main__.version))
    about.set_copyright("Copyright \xc2\xa9 %s" % __main__.copyright)
    about.set_website(__main__.website)
    about.set_authors(__main__.authors)
    
    about.show_all()
    
def get_tab_actions(window):
    def close_tab(action):
        window.close()
        
    to_add = (
        ("CloseTab", gtk.STOCK_CLOSE, "_Close Tab", None, None, close_tab),
        )
        
    tab_actions = gtk.ActionGroup("Tab")
    tab_actions.add_actions(to_add)
    
    return tab_actions
    
def get_urk_actions(ui):
    to_add = (
        ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, gtk.main_quit),
        
        ("HelpMenu", None, "_Help"),
            ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about)
        )
    
    urk_actions = gtk.ActionGroup("Urk")   
    urk_actions.add_actions(to_add)
    
    return urk_actions
        
class Window(gtk.VBox):
    def get_title(self):
        return self.__title
    
    def set_title(self, value):
        self.__title = value
        self.label.update()
    
    title = property(get_title, set_title)
    
    def get_activity(self):
        return self.__activity
    
    def set_activity(self, value):
        self.__activity = value
        self.label.update()
        
    activity = property(get_activity, set_activity)
    
    def activate(self):
        window_list.nb.set_current_page(window_list.nb.page_num(self))
    
    def close(self):
        events.trigger("Close", self)
        del window_list[self.network, self.type, self.id]
    
    def __init__(self, network, type, id, title=None):
        gtk.VBox.__init__(self, False)

        if network:
            id = network.normalize_case(id)
        
        self.network = network
        self.type = type
        self.id = id
        
        self.__title = title or id
        self.__activity = 0
        
        self.label = widgets.WindowLabel(self)
        self.label.show_all()
        
        MOD_MASK = 0
        for m in (gtk.gdk.CONTROL_MASK, gtk.gdk.MOD1_MASK, gtk.gdk.MOD3_MASK,
                        gtk.gdk.MOD4_MASK, gtk.gdk.MOD5_MASK):
            MOD_MASK |= m   

        def transfer_text(widget, event):
            modifiers_on = event.state & MOD_MASK

            if event.string and not modifiers_on:
                self.input.grab_focus()
                self.input.insert_text(event.string, -1)
                self.input.set_position(-1)
        
        self.connect("key-press-event", transfer_text)

def ServerWindow(network, type, id, title=None):
    w = window_list[network, type, id]

    if not w:
        w = Window(network, type, id, title or id)

        def write(text, activity_type=EVENT):
            if get_active() != w:
                w.activity |= activity_type
        
            w.output.write(text, activity_type)
        w.write = write

        w.output = widgets.TextOutput(w)
        w.input = widgets.TextInput(w)
        
        w.nick_label = widgets.NickEdit(w)
        
        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(w.output)
        
        w.pack_start(topbox)
        
        botbox = gtk.HBox()
        botbox.pack_start(w.input)
        botbox.pack_end(w.nick_label, expand=False)
        
        w.pack_end(botbox, expand=False)

        w.show_all()
        
        window_list[network, type, id] = w
    
    return w
    
QueryWindow = ServerWindow

def ChannelWindow(network, type, id, title=None):
    w = window_list[network, type, id]

    if not w:
        w = Window(network, type, id, title or id)
        
        def write(text, activity_type=EVENT):
            if get_active() != w:
                w.activity |= activity_type
        
            w.output.write(text, activity_type)
        w.write = write

        def set_nicklist(nicks):
            w.nicklist.userlist.clear()
            
            for nick in nicks:
                w.nicklist.userlist.append([nick])
        w.set_nicklist = set_nicklist

        w.output = widgets.TextOutput(w)
        w.input = widgets.TextInput(w)
        
        w.nicklist = widgets.Nicklist(w)
        
        w.nick_label = widgets.NickEdit(w)

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(w.output)
        
        pane = gtk.HPaned()
        pane.pack1(topbox, resize=True, shrink=False)
        pane.pack2(w.nicklist, resize=False, shrink=True)

        def set_pane_pos():
            pos = conf.get("ui-gtk/nicklist-width")
            if pos is not None:
                pos = pane.get_property("max-position") - conf.get("ui-gtk/nicklist-width")
            else:
                pos = pane.get_property("max-position")
        
            pane.set_position(pos)
        register_idle(set_pane_pos)

        def connect_save():
            def save_nicklist_width(pane, event):
                pos = pane.get_property("max-position") - pane.get_position()

                conf.set("ui-gtk/nicklist-width", pos)
        
            pane.connect("size-request", save_nicklist_width)
        register_idle(connect_save)

        botbox = gtk.HBox()
        botbox.pack_start(w.input)
        botbox.pack_end(w.nick_label, expand=False)
        
        w.pack_start(pane)        
        w.pack_end(botbox, expand=False)

        w.show_all()
        
        window_list[network, type, id] = w
    
    return w
  
class Tabs(dict):   
    def window_change(self, notebook, wptr, page_num):
        window = notebook.get_nth_page(page_num)
        
        window.activity = 0
        
        ui.set_title("%s - urk" % window.title)
        
        register_idle(window.input.grab_focus)
    
        events.trigger("Active", window)
    
    def __getitem__(self, nti):
        network, type, id = nti
        
        if network:
            id = network.normalize_case(id)

        if (network, type, id) in self:
            return dict.__getitem__(self, (network, type, id))

    def __setitem__(self, nti, window):
        network, type, id = nti
        
        if network:
            id = network.normalize_case(id)
        
        pos = len(self)
        if window.network:
            for i in reversed(range(pos)):
                if self.nb.get_nth_page(i).network == window.network:
                    pos = i+1
                    break
                    
        dict.__setitem__(self, (network, type, id), window)
                    
        self.nb.insert_page(window, None, pos)
        self.nb.set_tab_label(window, window.label)

    def __delitem__(self, item):
        network, type, id = item
        
        if network:
            id = network.normalize_case(id)

        self.nb.remove_page(self.nb.page_num(self[network, type, id]))
        dict.__delitem__(self, (network, type, id))
        
    def __init__(self):
        dict.__init__(self)
        
        self.nb = gtk.Notebook()
        
        tab_pos = conf.get("ui-gtk/tab-pos")
        if tab_pos is not None:
            self.nb.set_property("tab-pos", tab_pos)
        else:
            self.nb.set_property("tab-pos", gtk.POS_TOP)

        self.nb.set_border_width(10)
        self.nb.set_scrollable(True)
        self.nb.set_show_border(True)

        self.nb.connect("switch-page", self.window_change)

class UrkUI(gtk.Window):
    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        self.set_title("urk")
        self.set_icon(gtk.gdk.pixbuf_new_from_file("urk_icon.svg"))
        self.connect("delete_event", gtk.main_quit)

        # layout
        xy = conf.get("xy") or (-1, -1)
        wh = conf.get("wh") or (500, 500)

        self.move(*xy)
        self.set_default_size(*wh)
        
        def connect_save():        
            def save_xywh(*args):
                conf.set("xy", self.get_position())
                conf.set("wh", self.get_size())
            self.connect("configure_event", save_xywh)
        register_idle(connect_save)
        
        ui_manager = gtk.UIManager()
        
        self.add_accel_group(ui_manager.get_accel_group())
        ui_manager.add_ui_from_file(os.path.join(urk.path,"ui.xml"))
        ui_manager.insert_action_group(get_urk_actions(self), 0)
        
        menu = ui_manager.get_widget("/MenuBar")

        # widgets
        box = gtk.VBox(False)
        box.pack_start(menu, expand=False)
        box.pack_end(window_list.nb)

        self.add(box)
        self.show_all()
        
def get_window_for(network=None, type=None, id=None):
    if network and id:
        id = network.normalize_case(id)

    for n, t, i in list(window_list):
        if network and n != network:
            continue
        if type and t != type:
            continue
        if id and i != id:
            continue
            
        yield window_list[n, t, i]
        
def get_status_window(network):
    for n, t, i in window_list:
        if t == "status" and n == network:
            return window_list[n, t, i]
        
def get_active():
    active = window_list.nb.get_current_page()
    return window_list.nb.get_nth_page(active)

def start():
    if not window_list:
        first_network = irc.Network("irc.flugurgle.org")
        
        ServerWindow(
            first_network, 
            "status", 
            "Status Window", 
            "[%s]" % first_network.server
            )

        #ServerWindow(
        #    first_network, 
        #    "batus", 
        #    "Status Window", 
        #    "[%s]" % first_network.server
        #    )
        
        #first_window.set_nicklist(str(x) for x in range(100))
        
    #for i in range(1000):
    #    first_window.write("\x040000CC<\x04nick\x040000CC>\x04 text")
    #register_idle(gtk.main_quit)

    try:
        gtk.main()
    except KeyboardInterrupt:
        pass
    
# build our tab widget
window_list = Tabs()

# build our overall UI
ui = UrkUI()
