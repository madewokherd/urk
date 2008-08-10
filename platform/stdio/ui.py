from __future__ import division

import thread
import time
import signal
import traceback
import os

import windows
import events
import irc

# threading.Event would be ideal if not for the fact that Event.wait() works by
# sleeping for lots of short times.
if os.name == 'nt':
    import math
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_int, ctypes.c_uint]
    
    class Event(object):
        __fields__ = ['event_handle']
        
        _closehandle = kernel32.CloseHandle # apparently I can't expect this to exist while __del__ is being called
        
        def __init__(self):
            self.event_handle = kernel32.CreateEventA(0, 1, 0, 0)
            if not self.event_handle:
                raise ctypes.WinError()
        
        def isSet(self):
            return kernel32.WaitForSingleObject(self.event_handle, 0) == 0
        
        def set(self):
            if not kernel32.SetEvent(self.event_handle):
                raise ctypes.WinError()
        
        def clear(self):
            if not kernel32.ResetEvent(self.event_handle):
                raise ctypes.WinError()
        
        def wait(self, timeout=None):
            if timeout is None:
                kernel32.WaitForSingleObject(self.event_handle, 0xffffffff)
            else:
                kernel32.WaitForSingleObject(self.event_handle, min(int(math.ceil(timeout * 1000)), 0xfffffffe))
        
        def __del__(self):
            self._closehandle(self.event_handle)
else:
    import select
    
    class Event(object):
        __fields__ = ['r', 'w']
        
        def __init__(self):
            self.r, self.w = os.pipe()
        
        def isSet(self):
            readable, writeable, err = select.select([self.r], [], [], 0)
            return bool(readable)
        
        def set(self):
            if not self.isSet(): #not strictly necessary, but we'd like to keep the number of unread bytes small
                os.write(self.w, 'a')
        
        def clear(self):
            while self.isSet():
                os.read(self.r, 1)
        
        def wait(self, timeout=None):
            if timeout is None:
                select.select([self.r], [], [])
            else:
                select.select([self.r], [], [], timeout)
        
        def __del__(self):
            os.close(self.r)
            os.close(self.w)

#priority constants (ignored)
PRIORITY_HIGH = -100
PRIORITY_DEFAULT = 0
PRIORITY_HIGH_IDLE = 100
PRIORITY_DEFAULT_IDLE = 200
PRIORITY_LOW = 300

main_work_event = Event()

idle_tasks = []

timer_tasks = []

stop = False

def set_clipboard(text):
    pass

class Source(object):
    __slots__ = ['enabled', 'f', 'args', 'kwargs']
    def __init__(self, f=None, *args, **kwargs):
        self.enabled = True
        self.f = f
        self.args = args
        self.kwargs = kwargs
    def __call__(self):
        if self.enabled:
            try:
                self.f(*self.args, **self.kwargs)
            except:
                traceback.print_exc()
    def unregister(self):
        self.enabled = False

def register_idle(f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    source = Source(f, *args, **kwargs)
    idle_tasks.append(source)
    main_work_event.set()
    return source

def register_timer(t, f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    activate_time = time.time() + t/1000
    source = Source(f, *args, **kwargs)
    timer_tasks.append((activate_time, source))
    main_work_event.set()
    return source

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

def open_file(filename):
    pass

def start(command=''):
    #signal.signal(signal.SIGTERM, we_get_signal)
    
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

    while not windows.manager.quitted:
        main_work_event.clear()
        if idle_tasks:
            idle_tasks.pop(0)()
            continue
        current_time = time.time()
        next_timeout_time = time.time() + 3600
        for n, (t, task) in enumerate(timer_tasks):
            if current_time > t:
                timer_tasks.pop(n)
                task()
                break
            next_timeout_time = min(t, next_timeout_time)
        else:
            main_work_event.wait(next_timeout_time - current_time)

