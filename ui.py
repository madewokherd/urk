import sys #only needed for the stupid workaround

import gobject

sys.peth = list(sys.path)
import gtk
#stupid workaround
sys.path = sys.peth
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
    about = gtk.AboutDialog()
    
    about.set_name(urk.name+" (GTK+ Frontend)")
    about.set_version(".".join(str(x) for x in urk.version))
    about.set_copyright("Copyright \xc2\xa9 %s" % urk.copyright)
    about.set_website(urk.website)
    about.set_authors(urk.authors)
    
    about.show_all()
    
def get_urk_actions(ui):
    to_add = (
        ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, ui.exit),
        
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
        
    def focus(self):
        pass
    
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
        
        window_list[network, type, id] = self

class ServerWindow(Window):
    def focus(self):
        self.input.grab_focus()

    def write(self, text, activity_type=EVENT):
        if get_active() != self:
            self.activity |= activity_type

        self.output.write(text, activity_type)

    def __init__(self, network, type, id, title=None):
        Window.__init__(self, network, type, id, title or id)

        def transfer_text(widget, event):
            if event.string and not self.input.is_focus():
                self.input.grab_focus()
                self.input.set_position(-1)
                self.input.event(event)

        self.connect("key-press-event", transfer_text)

        self.output = widgets.TextOutput(self)
        self.input = widgets.TextInput(self)

        self.nick_label = widgets.NickEdit(self)

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)

        self.pack_start(topbox)

        botbox = gtk.HBox()
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)

        self.pack_end(botbox, expand=False)

        self.show_all()
    
QueryWindow = ServerWindow

class ChannelWindow(Window):
    def focus(self):
        self.input.grab_focus()

    def write(self, text, activity_type=EVENT):
        if get_active() != self:
            self.activity |= activity_type
    
        self.output.write(text, activity_type)

    def set_nicklist(self, nicks):
        self.nicklist.userlist.clear()
        
        for nick in nicks:
            self.nicklist.userlist.append([nick])

    def __init__(self, network, type, id, title=None):
        Window.__init__(self, network, type, id, title or id)
    
        def transfer_text(widget, event):
            if event.string and not self.input.is_focus():
                self.input.grab_focus()
                self.input.set_position(-1)
                self.input.event(event)

        self.connect("key-press-event", transfer_text)

        self.output = widgets.TextOutput(self)
        self.input = widgets.TextInput(self)
        
        self.nicklist = widgets.Nicklist(self)
        
        self.nick_label = widgets.NickEdit(self)

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)
        
        pane = gtk.HPaned()
        pane.pack1(topbox, resize=True, shrink=False)
        pane.pack2(self.nicklist, resize=False, shrink=True)

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
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)
        
        self.pack_start(pane)        
        self.pack_end(botbox, expand=False)

        self.show_all()
  
class Tabs(dict):   
    def window_change(self, notebook, wptr, page_num):
        window = notebook.get_nth_page(page_num)
        
        window.activity = 0
        
        ui.set_title("%s - urk" % window.title)
        
        register_idle(window.focus)
    
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

        self.nb.set_scrollable(True)
        self.nb.connect("switch-page", self.window_change)

class UrkUI(gtk.Window):
    def exit(self, *args):
        gtk.main_level() and gtk.main_quit()

        events.trigger("Exit")

    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        self.set_title("urk")
        
        try:
            self.set_icon(
                gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
                )
        except:
            pass

        self.connect("delete_event", self.exit)

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
        ui_manager.add_ui_from_file(urk.path("ui.xml"))
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
    return window_list.nb.get_nth_page(
            window_list.nb.get_current_page()
            )

def start():
    if not window_list:
        first_network = irc.Network()
    
        ServerWindow(
            first_network, 
            "status", 
            "Status Window", 
            "[%s]" % first_network.server
            )

    try:
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()
    except KeyboardInterrupt:
        ui.exit()
    
# build our tab widget
window_list = Tabs()

# build our overall UI
ui = UrkUI()
