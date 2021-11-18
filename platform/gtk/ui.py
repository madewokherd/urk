import sys #only needed for the stupid workaround
import os
import thread
import socket
import signal

import commands

from gi.repository import GObject
GObject.threads_init()

#stupid workaround
__sys_path = list(sys.path)
from gi.repository import Gtk
Gdk.threads_init()
sys.path = __sys_path

import irc
from conf import conf
import events

if 'URK_NO_REMOTE' not in os.environ:
    import remote

    if remote.run(' '.join(sys.argv[1:])):
        sys.exit(0)

import widgets
import windows

# Priority Constants
PRIORITY_HIGH = GObject.PRIORITY_HIGH
PRIORITY_DEFAULT = GObject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = GObject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = GObject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = GObject.PRIORITY_LOW

def set_clipboard(text):
    Gtk.clipboard_get(Gdk.SELECTION_CLIPBOARD).set_text(text)
    Gtk.clipboard_get(Gdk.SELECTION_PRIMARY).set_text(text)

class Source(object):
    __slots__ = ['enabled']
    def __init__(self):
        self.enabled = True
    def unregister(self):
        self.enabled = False

class GtkSource(object):
    __slots__ = ['tag']
    def __init__(self, tag):
        self.tag = tag
    def unregister(self):
        GObject.source_remove(self.tag)

def register_idle(f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        Gdk.threads_enter()
        try:
            return f(*args, **kwargs)
        finally:
            Gdk.threads_leave()
    return GtkSource(GObject.idle_add(callback, priority=priority))

def register_timer(time, f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        Gdk.threads_enter()
        try:
            return f(*args, **kwargs)
        finally:
            Gdk.threads_leave()
    return GtkSource(GObject.timeout_add(time, callback, priority=priority))

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

            register_idle(callback)

    thread.start_new_thread(thread_func, ())
    return is_stopped

set_style = widgets.set_style

#open_file(filename)
#opens a file or url using the "right" program
if hasattr(os,'startfile'):
    open_file = os.startfile
else:
    open_file_cmd = "" #cache results of searching for the os program
    os_commands = ( #list of commands to search for for opening files
        ('xdg-open', ('xdg-open',)),
        ('/usr/bin/open', ('/usr/bin/open',)),
        ('gnome-open', ('gnome-open',)),
        ('kfmclient', ('kfmclient','exec')),
        ('sensible-browser', ('sensible-browser')),
        )
    def open_file(filename):
        flags = GObject.SPAWN_LEAVE_DESCRIPTORS_OPEN | GObject.SPAWN_SEARCH_PATH
        filename = str(filename) #gobject won't accept unicode strings
        if conf.get('open-file-command'):
            command = conf['open-file-command'].split(' ') + [filename]
            try:
                GObject.spawn_async(command,flags=flags)
            except OSError:
                print "Unable to start %s" % command
        elif open_file_cmd:
            try:
                command = open_file_cmd + (filename,)
                GObject.spawn_async(command,flags=flags)
            except OSError:
                print "Unable to start %s" % command
        else:
            paths = os.getenv("PATH") or os.defpath
            for cmdfile, cmd in os_commands:
                for path in paths.split(os.pathsep):
                    if os.access(os.path.join(path,cmdfile),os.X_OK):
                        globals()['open_file_cmd'] = cmd
                        try:
                            command = cmd + (filename,)
                            GObject.spawn_async(command,flags=flags)
                        except OSError:
                            print "Unable to start %s" % command
                        return
            print "Unable to find a method to open %s." % filename

def we_get_signal(*what):
    GObject.idle_add(windows.manager.exit)

def start(command=''):
    #for i in range(10): windows[0].write("\x040000CC<\x04nick\x040000CC>\x04 text")

    #catch all the weird signals like SIGTERM and SIGSLORG
    signal.signal(signal.SIGTERM, we_get_signal)
    
    def trigger_start():
        events.trigger("Start")
        
        window = windows.manager.get_active()
        
        if not window:
           window = windows.new(windows.StatusWindow, irc.Network(), "status")
           window.activate()

        events.run(command, window, window.network)

        #for i in range(100):
        #    window.nicklist.append(chr(__import__('random').randint(ord('a'), ord('z'))), '<span color="green">%s</span>')
        #    window.write(file("urk/ui.py").read().splitlines()[i])
        
    register_idle(trigger_start)

    try:
        Gtk.main()
    except KeyboardInterrupt:
        windows.manager.exit()
