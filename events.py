import sys
import os
import traceback
import imp

class error(Exception):
    pass

class EventStopError(error):
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
                    except EventStopError:
                        return
                    except:
                        traceback.print_exc()

# Stop all processing of the current event now!
def halt():
    raise EventStopError

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

def handle_pyeval(e):
    loc = sys.modules.copy()
    loc.update(e.__dict__)
    try:
        e.window.write(repr(eval(' '.join(e.args), globals(), loc)))
    except:
        for line in traceback.format_exc().split('\n'):
            e.window.write(line)
    e.done = True

def handle_pyexec(e):
    loc = sys.modules.copy()
    loc.update(e.__dict__)
    try:
        exec ' '.join(e.args) in globals(), loc
    except:
        for line in traceback.format_exc().split('\n'):
            e.window.write(line)
    e.done = True

def handle_load(e):
    name = e.args[0]
    try:
        if load(name):
            e.done = True
        else:
            e.error_text = "The script is already loaded"
    except:
        traceback.print_exc()
        e.error_text = "Error loading the script"

def handle_unload(e):
    name = e.args[0]
    if is_loaded(name):
        unload(name)
        e.done = True
    else:
        e.error_text = "No such script is loaded"

def handle_reload(e):
    name = e.args[0]
    try:
        load(name, reloading=True)
        e.done = True
    except:
        traceback.print_exc()
        e.error_text = "Error loading the script"

def handle_scripts(e):
    e.window.write("Loaded scripts:")
    for name in loaded:
        e.window.write("* %s" % name)
    e.done = True

def handle_echo(e):
    e.window.write(' '.join(e.args))
    e.done = True

def handle_edit(e):
    try:
        args = find_script(e.args[0])
    except ImportError:
        e.error_text = "Couldn't find script: %s" % e.args[0]
        return
    if args[1]:
        args[1].close()
        import ui
        ui.open_file(args[2])
        del ui
        e.done = True
    else:
        e.error_text = "Couldn't find script: %s" % e.args[0]

def defCommand(e):
    if not e.done and 'handle_%s' % e.name in globals():
        globals()['handle_%s' % e.name](e)

register('Command', 'def', defCommand, '_events')
