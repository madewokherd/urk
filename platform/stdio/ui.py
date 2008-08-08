from __future__ import division

import thread
import time
import signal
import traceback

import windows
import events
import irc

#priority constants (ignored)
PRIORITY_HIGH = -100
PRIORITY_DEFAULT = 0
PRIORITY_HIGH_IDLE = 100
PRIORITY_DEFAULT_IDLE = 200
PRIORITY_LOW = 300

main_thread_id = thread.get_ident

main_work_mutex = thread.allocate_lock()
main_work_mutex.acquire()

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

def wake_main_thread():
    if thread.get_ident != main_thread_id and main_work_mutex.acquire(0):
        thread.interrupt_main()
        #don't release the mutex; it needs to be locked so nothing else interrupts the main thread

def register_idle(f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    source = Source(f, *args, **kwargs)
    idle_tasks.append(source)
    wake_main_thread()
    return source

def register_timer(t, f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    activate_time = time.time() + t/1000
    source = Source(f, *args, **kwargs)
    timer_tasks.append((activate_time, source))
    wake_main_thread()
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
        if idle_tasks:
            idle_tasks.pop(0)()
            continue
        current_time = time.time()
        next_timeout_time = current_time + 0.5 #FIXME: using short waits because interrupt_main() doesn't work while main is sleeping
        for n, (t, task) in enumerate(timer_tasks):
            if current_time > t:
                timer_tasks.pop(n)
                task()
                break
            next_timeout_time = min(t, next_timeout_time)
        else:
            try:
                main_work_mutex.release()
                time.sleep(next_timeout_time - current_time)
                if main_work_mutex.acquire(0) == False:
                    #some thread is about to send a KeyboardInterrupt
                    time.sleep(10000)
            except KeyboardInterrupt:
                if main_work_mutex.acquire(0) == True:
                    #KeyboardInterrupt originated from outside the process
                    raise
            finally:
                main_work_mutex.acquire(0)

