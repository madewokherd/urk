import sys
import os
import traceback
import imp

pyending = os.extsep + 'py'

class error(Exception):
    pass

class EventStopError(error):
    pass

class CommandError(error):
    pass

class data(object):
    done = False
    quiet = False
    
    def __init__(self, **kwargs):
        for attr in kwargs.items():
            setattr(self, *attr)

trigger_sequence = ("setup", "pre", "def", "on", "post")

events = {}
loaded = {}

# An event has occurred, the e_name event!
def trigger(e_name, e_data=None):
    #print 'Event:', e_name, e_data

    failure = True
    error = None
    if e_name in events:
        for e_stage in trigger_sequence:
            if e_stage in events[e_name]:
                for f_ref, s_name in events[e_name][e_stage]:
                    try:
                        f_ref(e_data)
                    except EventStopError:
                        return
                    except CommandError, e:
                        error = e.args
                        continue
                    except:
                        traceback.print_exc()
                    failure = False
    if failure:
        return error

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

# turn a filename (or module name) and trim it to the name of the module
def get_scriptname(name):
    s_name = os.path.basename(name)
    if s_name.endswith(pyending):
        s_name = s_name[:-len(pyending)]
    return s_name

#take a given script name and turn it into a filename
def get_filename(name):
    # split the directory and filename
    dirname = os.path.dirname(name)
    s_name = get_scriptname(name)
    
    for path in dirname and (dirname,) or sys.path:
        filename = os.path.join(path, s_name + pyending)
        if os.access(filename, os.R_OK):
            return filename

    raise ImportError("No urk script %s found" % name) 

# register the events defined by obj
def register_all(name, obj):
    # we look through everything defined in the file    
    for f in dir(obj):
        # for each bit of the event sequence
        for e_stage in trigger_sequence:

            # if the function is for this bit
            if f.startswith(e_stage):
            
                # get a reference to a function
                f_ref = getattr(obj, f)
                
                # normalise to the event name                
                e_name = f.replace(e_stage, "", 1)
                
                # add our function to the right event section
                register(e_name, e_stage, f_ref, name)
                
                break

#load a .py file into a new module object without affecting sys.modules
def load_pyfile(filename):
    s_name = get_scriptname(filename)

    module = imp.new_module(s_name)
    module.__file__ = filename
    
    f = file(filename,"U")
    source = f.read()
    f.close()

    exec compile(source, filename, "exec") in module.__dict__
    return module

# Load a python script and register
# the functions defined in it for events.
# Return True if we loaded the script, False if it was already loaded
def load(name):
    s_name = get_scriptname(name)
    filename = get_filename(name)
    
    if s_name in loaded:
        return False
    
    loaded[s_name] = None
    
    try:
        loaded[s_name] = load_pyfile(filename)
    except:
        del loaded[s_name]
        raise
    
    register_all(s_name, loaded[s_name])
    
    return True

# Is the script with the given name loaded?
def is_loaded(name):
    return get_scriptname(name) in loaded

# Remove any function which was defined in the given script
def unload(name):
    s_name = get_scriptname(name)
    
    del loaded[s_name]

    for e_name in list(events):
        for e_stage in list(events[e_name]):
            to_check = events[e_name][e_stage]

            events[e_name][e_stage] = [(f, m) for f, m in to_check if m != s_name]
            
            if not events[e_name][e_stage]:
                del events[e_name][e_stage]
        
        if not events[e_name]:
            del events[e_name]

def reload(name):
    s_name = get_scriptname(name)

    if s_name not in loaded:
        return False
    
    temp = loaded[s_name]
    
    unload(s_name)

    try:
        load(name)
        return True
    except:
        loaded[s_name] = temp
        register_all(s_name, temp)
        raise

def run(text, window, network):
    split = text.split(' ')

    c_data = data(name=split[0], text=text, window=window, network=network)

    if len(split) > 1 and split[1].startswith('-'):
        c_data.switches = set(split[1][1:])
        c_data.args = split[2:]
    else:
        c_data.switches = set()
        c_data.args = split[1:]

    event_name = "Command" + c_data.name.capitalize()    
    if event_name in events:
        result = trigger(event_name, c_data)
        
        if result:
            c_data.window.write("* /%s: %s" % (c_data.name, result[0]))
    else:
        trigger("Command", c_data)
        
        if not c_data.done:
            c_data.window.write("* /%s: No such command exists" % (c_data.name))

# Script stuff starts here

def onCommandPyeval(e):
    loc = sys.modules.copy()
    loc.update(e.__dict__)
    try:
        result = repr(eval(' '.join(e.args), loc))
        if 's' in e.switches:
            run(
                'say - %s => %s' % (' '.join(e.args),result),
                e.window,
                e.network
                )
        else:
            e.window.write(result)
    except:
        for line in traceback.format_exc().split('\n'):
            e.window.write(line)

def onCommandPyexec(e):
    loc = sys.modules.copy()
    loc.update(e.__dict__)
    try:
        exec ' '.join(e.args) in loc
    except:
        for line in traceback.format_exc().split('\n'):
            e.window.write(line)

def onCommandLoad(e):
    if e.args:
        name = e.args[0]
    else:
        e.window.write('Usage: /load scriptname')

    try:
        if load(name):
            e.window.write("* The script '%s' has been loaded." % name)
        else:
            raise CommandError("The script is already loaded; use /reload instead")
    except:
        e.window.write(traceback.format_exc(), line_ending='')
        raise CommandError("Error loading the script")

def onCommandUnload(e):
    if e.args:
        name = e.args[0]
    else:
        e.window.write('Usage: /unload scriptname')

    if is_loaded(name):
        unload(name)
    else:
        raise CommandError("No such script is loaded")

def onCommandReload(e):
    if e.args:
        name = e.args[0]
    else:
        e.window.write('Usage: /reload scriptname')

    try:
        if reload(name):
            e.window.write("* The script '%s' has been reloaded." % name)
        else:
            raise CommandError("The script isn't loaded yet; use /load instead") 
    except:
        e.window.write(traceback.format_exc(), line_ending='')

def onCommandScripts(e):
    e.window.write("Loaded scripts:")
    for name in loaded:
        e.window.write("* %s" % name)

def onCommandEcho(e):
    e.window.write(' '.join(e.args))

name = ''
for name in globals():
    if name.startswith('onCommand'):
        register(name[2:], "on", globals()[name], '_events')
del name
