import sys #only needed for the stupid workaround
import os
import thread
import socket

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

class SocketSource(object):
    writeable_tag = None
    tags = None
    
    socket = None
    
    def on_connect(self):
        pass

    def on_readable(self):
        pass

    def on_disconnect(self, errno, msg):
        pass

    def __init__(self, socket, on_connect=None, on_readable=None, on_disconnect=None):
        self.socket = socket
        self._connected = False
        self._sendbuffer = ""
        
        if on_connect:
            self.on_connect = on_connect
        
        if on_readable:
            self.on_readable = on_readable
        
        if on_disconnect:
            self.on_disconnect = on_disconnect
        
        self.sources = []
        
        self.tags = [gobject.io_add_watch(socket, gobject.IO_ERR, self._on_disconnect)]
        self.tags.append(gobject.io_add_watch(socket, gobject.IO_HUP, self._on_disconnect))
        self.writeable_tag = gobject.io_add_watch(socket, gobject.IO_OUT, self._on_writeable)
        self.tags.append(gobject.io_add_watch(socket, gobject.IO_IN, self._on_readable))
    
    def _on_writeable(self, fd, condition):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            self.on_disconnect(err, os.strerror(err))
            self.unregister()
        else:
            if not self._connected:
                self.on_connect()
                self._connected = True
            if self._sendbuffer:
                n = self.socket.send(self._sendbuffer, socket.MSG_DONTWAIT)
                self._sendbuffer = string[n:]
            if not self._sendbuffer and self.writeable_tag:
                gobject.source_remove(self.writeable_tag)
                self.writeable_tag = None
        return True
    
    def _on_readable(self, fd, condition):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            self.on_disconnect(err, os.strerror(err))
            self.unregister()
        else:
            self.on_readable()
        return True
    
    def _on_disconnect(self, fd, condition):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        self.on_disconnect(err, err and os.strerror(err) or "Connection closed by remote host")
        self.unregister()
        return True
    
    def write(self, string):
        #socket.send doesn't guarantee all the data will be sent and sendall may block
        #the solution is to use this function
        if self._sendbuffer:
            self._sendbuffer += string
        else:
            n = self.socket.send(string, socket.MSG_DONTWAIT)
            self._sendbuffer = string[n:]
            if self._sendbuffer and not self.writeable_tag:
                self.writeable_tag = gobject.io_add_watch(self.socket, gobject.IO_OUT, self._on_writeable)
    
    def unregister(self):
        if self.writeable_tag:
            gobject.source_remove(self.writeable_tag)
            self.writeable_tag = None
        for tag in self.tags:
            gobject.source_remove(tag)
        self.tags = ()

register_socket = SocketSource

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
        flags = gobject.SPAWN_LEAVE_DESCRIPTORS_OPEN | gobject.SPAWN_SEARCH_PATH
        filename = str(filename) #gobject won't accept unicode strings
        if conf.get('open-file-command'):
            command = conf['open-file-command'].split(' ') + [filename]
            try:
                gobject.spawn_async(command,flags=flags)
            except OSError:
                print "Unable to start %s" % command
        elif open_file_cmd:
            try:
                command = open_file_cmd + (filename,)
                gobject.spawn_async(command,flags=flags)
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
                            gobject.spawn_async(command,flags=flags)
                        except OSError:
                            print "Unable to start %s" % command
                        return
            print "Unable to find a method to open %s." % filename

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
