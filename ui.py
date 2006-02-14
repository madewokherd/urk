import sys #only needed for the stupid workaround
import os
import thread

import commands

import gobject

#stupid workaround
__sys_path = list(sys.path)
import gtk
sys.path = __sys_path

import urk
import irc
from conf import conf
import events
import widgets

from windows import StatusWindow, QueryWindow, ChannelWindow

# Priority Constants
PRIORITY_HIGH = gobject.PRIORITY_HIGH
PRIORITY_DEFAULT = gobject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = gobject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = gobject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = gobject.PRIORITY_LOW

def set_clipboard(text):
    gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(text)
    gtk.clipboard_get(gtk.gdk.SELECTION_SECONDARY).set_text(text)

class Source:
    __slots__ = ['enabled']
    enabled = True
    def unregister(self):
        self.enabled = False

class GtkSource:
    __slots__ = ['tag']
    def __init__(self, tag):
        self.tag = tag
    def unregister(self):
        gobject.source_remove(self.tag)

def register_idle(f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        return f(*args, **kwargs)
    return GtkSource(gobject.idle_add(callback, priority=priority))

def register_timer(time, f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        return f(*args, **kwargs)
    return GtkSource(gobject.timeout_add(time, callback, priority=priority))

def fork(cb, f, *args, **kwargs):
    is_stopped = Source()
    def thread_func():
        try:
            result, error = f(*args, **kwargs), None
        except Exception, e:
            result, error = None, e
            
        if is_stopped.enabled:
            def callback():           
                if is_stopped.enabled:
                    cb(result, error)

            gobject.idle_add(callback)

    thread.start_new_thread(thread_func, ())
    return is_stopped

set_style = widgets.set_style

# Window activity Constants
HILIT = 4
TEXT = 2
EVENT = 1

activity_markup = {
    HILIT: "<span style='italic' foreground='#00F'>%s</span>",
    TEXT: "<span foreground='red'>%s</span>",
    EVENT: "<span foreground='#363'>%s</span>",
    }

#open_file(filename)
#opens a file or url using the "right" program
if hasattr(os,'startfile'):
    open_file = os.startfile
else:
    open_file_cmd = "" #cache results of searching for the os program
    os_commands = ( #list of commands to search for for opening files
        ('gnome-open', ('gnome-open',)),
        ('kfmclient', ('kfmclient','exec')),
        ('sensible-browser', ('sensible-browser')),
        )
    def open_file(filename):
        if conf.get('open-file-command'):
            import subprocess
            command = conf['open-file-command'].split(' ') + [filename]
            try:
                process = os.spawnvp(os.P_NOWAIT,command[0], command)
                _kill_the_zombies(process)
            except OSError:
                print "Unable to start %s" % command
        elif open_file_cmd:
            try:
                command = open_file_cmd + (filename,)
                process = os.spawnvp(os.P_NOWAIT,command[0], command)
                _kill_the_zombies(process)
            except OSError:
                print "Unable to start %s" % command
        else:
            import subprocess
            paths = os.getenv("PATH") or os.defpath
            for cmdfile, cmd in os_commands:
                for path in paths.split(os.pathsep):
                    if os.access(os.path.join(path,cmdfile),os.X_OK):
                        globals()['open_file_cmd'] = cmd
                        try:
                            command = cmd + (filename,)
                            process = os.spawnvp(os.P_NOWAIT,command[0], command)
                            _kill_the_zombies(process)
                        except OSError:
                            print "Unable to start %s" % command
                        return
            print "Unable to find a method to open %s." % filename
    #ugly hack to make sure we get rid of zombie processes
    def _kill_the_zombies(process):
        pid, status = os.waitpid(process,os.WNOHANG)
        if pid == 0:
            register_timer(5000, _kill_the_zombies, process)

def urk_about(*args):
    about = gtk.AboutDialog()
    
    about.set_name(urk.name+" (GTK+ Frontend)")
    about.set_version(".".join(str(x) for x in urk.version))
    about.set_copyright("Copyright \xc2\xa9 %s" % urk.copyright)
    about.set_website(urk.website)
    about.set_authors(urk.authors)
    
    about.show_all()
        
class Window(gtk.VBox):
    def mutate(self, newrole, network, id):
        self.hide()
    
        for child in self.get_children():
            self.remove(child)
            
        self.role = newrole
        self.role(self)

        self.network = network
        self.id = id           
        
    def get_id(self):
        if self.network:
            return self.network.norm_case(self.__id)
        else:
            return self.__id
            
    def set_id(self, id):
        self.__id = id
        self.update()

    id = property(get_id, set_id)
    
    def get_title(self):
        return self.__id

    def __get_title(self):
        return self.get_title()
    
    def set_title(self, title):
        self.update()
        
    title = property(__get_title, set_title)

    def get_activity(self):
        return self.__activity
    
    def set_activity(self, value):
        self.__activity = value
        self.update()
        
    activity = property(get_activity, set_activity)
    
    def focus(self):
        pass
    
    def activate(self):
        windows.manager.set_active(self)
        self.focus()
    
    def close(self):
        events.trigger("Close", self)
        windows.remove(self)
        
    def update(self):
        windows.manager.update(self)

    def __init__(self, role, network, id):
        gtk.VBox.__init__(self, False)
        
        self.role = role
        self.network = network
        self.__id = id
        
        self.role(self)
        
        self.__activity = 0
        

  
class Windows(list):     
    def new(self, role, network, id):
        w = self.get(role, network, id)
        
        if not w:
            w = Window(role, network or irc.Network(), id)
            self.append(w)

        return w
        
    def get(self, role, network, id):
        if network:
            id = network.norm_case(id)
            
        for w in self:
            if (w.role, w.network, w.id) == (role, network, id):
                return w

    def append(self, window):
        list.append(self, window)
        self.manager.add(window)    

    def remove(self, window):
        list.remove(self, window)
        self.manager.remove(window)

    def __init__(self):
        list.__init__(self)
        self.manager = widgets.UrkUITabs()

def get_window_for(role=None, network=None, id=None):
    if network and id:
        id = network.norm_case(id)

    for w in list(windows):
        for a, b in zip((role, network, id), (w.role, w.network, w.id)):
            if a and a != b:
                break
        else:
            yield w
            
def get_default_window(network):
    window = windows.manager.get_active()
    if window.network == network:
        return window

    # There can be only one...
    for window in get_window_for(network=network):
        return window

def start(command=''):
    #for i in range(10): windows[0].write("\x040000CC<\x04nick\x040000CC>\x04 text")
    
    def trigger_start():
        events.trigger("Start")
        
        if not windows:
            windows.new(StatusWindow, None, "status").activate()
        
        window = windows.manager.get_active()
        events.run(command, window, window.network)
        
        #for i in range(100):
        #    window.write(file("urk/ui.py").read().splitlines()[i])
        
    register_idle(trigger_start)

    try:
        gtk.threads_enter()
        #while gtk.events_pending(): gtk.main_iteration()
        gtk.main()
        gtk.threads_leave()
    except KeyboardInterrupt:
        windows.manager.exit()
    
# build our tab widget
windows = Windows()
