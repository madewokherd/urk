import sys #only needed for the stupid workaround
import os

import gobject

#stupid workaround
sys.peth = list(sys.path)
import gtk
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

#open_file(filename)
#opens a file or url using the "right" program
open_file_cmd = "" #cache results of searching for the os program
os_commands = ( #list of commands to search for for opening files
    ('gnome-open', 'gnome-open %s'),
    ('kfmclient', 'kfmclient exec %s'),
    )
def open_file(filename):
    if conf.get('open-file-command'):
        os.popen(conf.get('open-file-command') % filename)
    elif hasattr(os, 'startfile'):
        os.startfile(filename)
    elif open_file_cmd:
        os.popen(open_file_cmd % filename)
    else:
        #look for a command we can use
        paths = os.getenv("PATH") or os.defpath
        for cmdfile, cmd in os_commands:
            for path in paths.split(os.pathsep):
                if os.access(os.path.join(path,cmdfile),os.X_OK):
                    globals()['open_file_cmd'] = cmd
                    os.popen(cmd % filename)
                    break
        else:
            print "Unable to find a method to open %s" % filename


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
        windows.nb.set_current_page(windows.nb.page_num(self))
    
    def close(self):
        events.trigger("Close", self)
        del windows[self.network, type(self), self.id]
        
    def focus(self):
        pass
    
    def __init__(self, network, id, title=None):
        gtk.VBox.__init__(self, False)

        if network:
            id = network.normalize_case(id)
        
        self.network = network
        self.id = id
        
        self.__title = title or id
        self.__activity = 0
        
        self.label = widgets.WindowLabel(self)
        self.label.show_all()

class StatusWindow(Window):
    def focus(self):
        self.input.grab_focus()

    def write(self, text, activity_type=EVENT):
        if get_active() != self:
            self.activity |= activity_type

        self.output.write(text, activity_type)

    def __init__(self, network, id, title=None):
        Window.__init__(self, network, id, title)

        def transfer_text(widget, event):
            if event.string and not self.input.is_focus():
                self.input.grab_focus()
                self.input.set_position(-1)
                self.input.event(event)

        self.connect("key-press-event", transfer_text)

        self.output = widgets.TextOutput(self)

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(self.output)

        self.pack_start(topbox)
        
        self.input = widgets.TextInput(self)
        self.nick_label = widgets.NickEdit(self)

        botbox = gtk.HBox()
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)

        self.pack_end(botbox, expand=False)

        self.show_all()
    
class QueryWindow(StatusWindow):
    pass

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

    def __init__(self, network, id, title=None):    
        Window.__init__(self, network, id, title)
    
        def transfer_text(widget, event):
            if event.string and not self.input.is_focus():
                self.input.grab_focus()
                self.input.set_position(-1)
                self.input.event(event)

        self.connect("key-press-event", transfer_text)

        self.output = widgets.TextOutput(self)
        self.nicklist = widgets.Nicklist(self)

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
        
        self.pack_start(pane)
        
        self.input = widgets.TextInput(self)
        self.nick_label = widgets.NickEdit(self)

        botbox = gtk.HBox()
        botbox.pack_start(self.input)
        botbox.pack_end(self.nick_label, expand=False)
      
        self.pack_end(botbox, expand=False)

        self.show_all()
  
class WindowTabs(dict):   
    def window_change(self, notebook, wptr, page_num):
        window = notebook.get_nth_page(page_num)
        
        window.activity = 0
        
        ui.set_title("%s - urk" % window.title)
        
        register_idle(window.focus)
    
        events.trigger("Active", window)
        
    def new(self, type, network, id, title=None):
        if (type, network,id) not in self:
            self[type, network, id] = type(network, id, title)
              
        return self[type, network, id]
        
    def __contains__(self, tni):
        t, n, id = tni
        
        if n:
            id = n.normalize_case(id)
            
        return dict.__contains__(self, (t, n, id))
    
    def __getitem__(self, tni):
        t, n, id = tni
        
        if n:
            id = n.normalize_case(id)

        if dict.__contains__(self, (t, n, id)):
            return dict.__getitem__(self, (t, n, id))

    def __setitem__(self, tni, window):
        t, n, id = tni
        
        if n:
            id = n.normalize_case(id)
        
        pos = len(self)
        if window.network:
            for i in reversed(range(pos)):
                if self.nb.get_nth_page(i).network == window.network:
                    pos = i+1
                    break
                    
        dict.__setitem__(self, (t, n, id), window)
                    
        self.nb.insert_page(window, None, pos)
        self.nb.set_tab_label(window, window.label)

    def __delitem__(self, item):
        t, n, id = tni
        
        if n:
            id = n.normalize_case(id)

        self.nb.remove_page(self.nb.page_num(self[t, n, id]))
        dict.__delitem__(self, (t, n, id))
        
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
        events.trigger("Exit")
        gtk.main_level() and gtk.main_quit()

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
        box.pack_end(windows.nb)

        self.add(box)
        self.show_all()
        
def get_window_for(type=None, network=None, id=None):
    if network and id:
        id = network.normalize_case(id)

    for t, n, i in list(windows):
        if type and t != type:
            continue
        if network and n != network:
            continue
        if id and i != id:
            continue
            
        yield windows[t, n, i]
        
def get_status_window(network):
    for t, n, i in windows:
        if t == StatusWindow and n == network:
            return windows[t, n, i]
        
def get_active():
    return windows.nb.get_nth_page(
            windows.nb.get_current_page()
            )

def start():
    if not windows:
        first_network = irc.Network()
        
        windows.new(
            StatusWindow,
            first_network,
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
windows = WindowTabs()

# build our overall UI
ui = UrkUI()
