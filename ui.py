import sys #only needed for the stupid workaround
import os
import threading

import commands

import gobject

#stupid workaround
__sys_path = list(sys.path)
import gtk
sys.path = __sys_path

import irc
from conf import conf
import events

import widgets
import windows

# Priority Constants
PRIORITY_HIGH = gobject.PRIORITY_HIGH
PRIORITY_DEFAULT = gobject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = gobject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = gobject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = gobject.PRIORITY_LOW

def set_clipboard(text):
    gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(text)
    gtk.clipboard_get(gtk.gdk.SELECTION_SECONDARY).set_text(text)

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

class UrkForker(threading.Thread):
    def unregister(self):
        self.enabled = False

    def run(self):
        try:
            result, error = self.task(*self.args, **self.kwargs), None
        except Exception, e:
            result, error = None, e
            
        if self.enabled:
            def callback():
                self.callback(result, error)
        
            gobject.idle_add(callback)
    
    def __init__(self, callback, task, args=(), kwargs={}):
        super(UrkForker, self).__init__()

        self.callback = callback
        self.task = task
        self.args = args
        self.kwargs = kwargs
        
        self.enabled = True

def fork(cb, f, *args, **kwargs):
    forker = UrkForker(cb, f, args, kwargs)
    forker.start()
    
    return forker

set_style = widgets.set_style

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

def start(command=''):
    #for i in range(10): windows[0].write("\x040000CC<\x04nick\x040000CC>\x04 text")
    
    windows.manager = widgets.UrkUITabs()
    
    def trigger_start():
        events.trigger("Start")
        
        window = windows.manager.get_active()
        
        if not window:
           window =  windows.new(windows.StatusWindow, None, "status")
           window.activate()

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
