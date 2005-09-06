import sys
import os
import traceback
import imp

class error(Exception):
    pass

class data:
    done = False
    quiet = False
    
    def __init__(self, **kwargs):
        for attr in kwargs.items():
            setattr(self, *attr)

trigger_sequence = ("setup", "pre", "def", "on", "post")

events = {}
loaded = {} # FIXME: dict for when we need some info on it

# An event has occurred, the e_name event!
def trigger(e_name, e_data=None):
    if e_name in events:
        for e_stage in trigger_sequence:
            if e_stage in events[e_name]:
                for f_ref, s_name in events[e_name][e_stage]:
                    try:
                        f_ref(e_data)
                    except:
                        traceback.print_exc()

# Registers a specific function with an event at the given sequence stage.
def register(e_name, e_stage, f_ref, s_name=""):
    if e_name not in events:
        events[e_name] = {}
        
    if e_stage not in events[e_name]:
        events[e_name][e_stage] = []
        
    events[e_name][e_stage] += [(f_ref, s_name)]

#take a given script name and turn it into a tuple for use with load_module
def find_script(s_name):
    # split the directory and filename
    dirname = os.path.dirname(s_name)
    filename = os.path.basename(s_name)
    
    for suffix, dummy, dummy in imp.get_suffixes():
        #trim things like .py
        if filename.endswith(suffix):
            filename = filename[:-len(suffix)]
            break
    
    return (filename,) + imp.find_module(filename, (dirname and [dirname]) or None)

# Load a python script and register
# the functions defined in it for events.
# Return True if we loaded the script, False if it was already loaded
def load(s_name, reloading = False):
    args = find_script(s_name)
    f = args[1]
    filename = args[2]
    
    if not reloading and filename in loaded:
        f.close()
        return False
    
    loaded[filename] = None
    
    try:
        if reloading:
            unload(filename)
        
        imported = imp.load_module(*args)
    except Exception, e:
        del loaded[filename]
        f.close()
        raise e
    f.close()
    
    # we look through everything defined in the file    
    for f in dir(imported):
        # for each bit of the event sequence
        for e_stage in trigger_sequence:

            # if the function is for this bit
            if f.startswith(e_stage):
            
                # get a reference to a function
                f_ref = getattr(imported, f)
                
                # normalise to the event name                
                e_name = f.replace(e_stage, "", 1)
                
                # add our function to the right event section
                register(e_name, e_stage, f_ref, filename)
                
                break
    
    return True

# Is the script with the given name loaded?
def is_loaded(s_name):
    name, f, filename, filetype = find_script(s_name)
    f.close()
    
    return filename in loaded

# Remove any function which was defined in the given script
def unload(s_name):
    name, f, filename, filetype = find_script(s_name)
    f.close()

    del loaded[filename]

    for e_name in events:
        for e_stage in events[e_name]:
            to_check = events[e_name][e_stage]
        
            events[e_name][e_stage] = [(f, m) for f, m in to_check if m != filename]

def run_command(text, window, network):
    if not text:
        return

    split = text.split(" ")

    c_data = data()
    c_data.text = text
    
    c_data.name = split[0]

    if len(split) > 1 and split[1].startswith("-"):
        c_data.switches = set(split[1][1:])
        c_data.args = split[2:]
    else:
        c_data.switches = set()
        c_data.args = split[1:]

    c_data.window = window
    c_data.network = network

    c_data.error_text = 'No such command exists'
    
    trigger('Command', c_data)
    
    if not c_data.done:
        c_data.window.write("* /%s: %s" % (c_data.name, c_data.error_text))

def handle_pyeval(event):
    try:
        event.window.write(repr(eval(' '.join(event.args), globals(), event.__dict__)))
    except:
        for line in traceback.format_exc().split('\n'):
            event.window.write(line)
    event.done = True

def handle_pyexec(event):
    try:
        exec ' '.join(event.args) in globals(), event.__dict__
    except:
        for line in traceback.format_exc().split('\n'):
            event.window.write(line)
    event.done = True

def handle_load(event):
    name = event.args[0]
    try:
        if load(name):
            event.done = True
        else:
            event.error_text = "The script is already loaded"
    except:
        traceback.print_exc()
        event.error_text = "Error loading the script"

def handle_unload(event):
    name = event.args[0]
    if is_loaded(name):
        unload(name)
        event.done = True
    else:
        event.error_text = "No such script is loaded"

def handle_reload(event):
    name = event.args[0]
    try:
        load(name, reloading=True)
        event.done = True
    except:
        traceback.print_exc()
        event.error_text = "Error loading the script"

def handle_scripts(event):
    event.window.write("Loaded scripts:")
    for name in loaded:
        event.window.write("* %s" % name)
    event.done = True

command_handlers = {
    'pyeval': handle_pyeval,
    'pyexec': handle_pyexec,
    'load': handle_load,
    'unload': handle_unload,
    'reload': handle_reload,
    'scripts': handle_scripts,
    }

def defCommand(event):
    if not event.done and event.name in command_handlers:
        command_handlers[event.name](event)

register('Command', 'def', defCommand, '_events')
