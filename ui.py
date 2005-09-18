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
                    return
        print "Unable to find a method to open %s." % filename

def urk_about(action):
    about = gtk.AboutDialog()
    
    about.set_name(urk.name+" (GTK+ Frontend)")
    about.set_version(".".join(str(x) for x in urk.version))
    about.set_copyright("Copyright \xc2\xa9 %s" % urk.copyright)
    about.set_website(urk.website)
    about.set_authors(urk.authors)
    
    about.show_all()
        
class Window(gtk.VBox):
    def get_id(self):
        if self.network:
            return self.network.norm_case(self.__id)
        else:
            return self.__id

    id = property(get_id)

    def get_title(self):
        return self.__id
    
    def get_activity(self):
        return self.__activity
    
    def set_activity(self, value):
        self.__activity = value
        self.title.update()
        
    activity = property(get_activity, set_activity)
    
    def activate(self):
        windows.manager.set_active(self)
    
    def close(self):
        events.trigger("Close", self)
        windows.remove(self)
        
    def focus(self):
        pass
    
    def __init__(self, network, id):
        gtk.VBox.__init__(self, False)
        
        self.network = network
        self.__id = id
        
        self.__activity = 0
        
        self.title = widgets.WindowLabel(self)
        self.title.show_all()

class StatusWindow(Window):
    def get_title(self):
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server

    def focus(self):
        self.input.grab_focus()

    def write(self, text, activity_type=EVENT):
        if windows.manager.get_active() != self:
            self.activity |= activity_type

        self.output.write(text, activity_type)

    def __init__(self, network, id):
        Window.__init__(self, network, id)

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
    def get_title(self):
        return Window.get_title(self)

class ChannelWindow(StatusWindow):
    def get_title(self):
        return Window.get_title(self)

    def set_nicklist(self, nicks):
        self.nicklist.userlist.clear()
        
        for nick in nicks:
            self.nicklist.userlist.append([nick])

    def __init__(self, network, id):    
        Window.__init__(self, network, id)
    
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
            pane.set_position(
                pane.get_property("max-position") - (conf.get("ui-gtk/nicklist-width") or 0)
                )
        register_idle(set_pane_pos)

        def connect_save():
            def save_nicklist_width(pane, event):
                conf.set(
                    "ui-gtk/nicklist-width", 
                    pane.get_property("max-position") - pane.get_position()
                    )
        
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
  
class WindowTabs(list):       
    def new(self, type, network, id):
        w = self.get(type, network, id)
        
        if not w:
            w = type(network, id)
            self.append(w)
              
        return w
        
    def get(self, t, network, id):
        if network:
            id = network.norm_case(id)
            
        for w in self:
            if (type(w), w.network, w.id) == (t, network, id):
                return w

    def append(self, window):
        list.append(self, window)
        self.manager.add(window)    

    def remove(self, window):
        list.remove(self, window)
        self.manager.remove(window)

    def __init__(self):
        list.__init__(self)
        self.manager = widgets.WindowListTabs()

class UrkUI(gtk.Window):
    def exit(self, *args):
        events.trigger("Exit")
        gtk.main_level() and gtk.main_quit()

    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        
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
        
        menus = (
            ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, self.exit),
        
            ("HelpMenu", None, "_Help"),
            ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about),
            )
    
        actions = gtk.ActionGroup("Urk")   
        actions.add_actions(menus)
        
        ui_manager = gtk.UIManager()        
        ui_manager.insert_action_group(actions, 0)
        
        self.add_accel_group(ui_manager.get_accel_group())
        ui_manager.add_ui_from_file(urk.path("ui.xml"))
        
        menu = ui_manager.get_widget("/MenuBar")

        # widgets
        box = gtk.VBox(False)
        box.pack_start(menu, expand=False)
        box.pack_end(windows.manager)

        self.add(box)
        self.show_all()
        
def get_window_for(type=None, network=None, id=None):
    if network and id:
        id = network.norm_case(id)

    for w in list(windows):
        for a, b in zip((type, network, id), (__builtins__['type'](w), w.network, w.id)):
            if a and a != b:
                break
        else:
            yield w
            
def get_default_window(network):
    # There can be only one...
    for window in get_window_for(network=network):
        return window

def start():
    if not windows:
        windows.new(StatusWindow, irc.Network(), "status").activate()
        
    #register_idle(ui.exit)

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

set_title = ui.set_title
