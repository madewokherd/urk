import sys
import os
import traceback
import imp

class error(Exception):
    pass

class EventStopError(error):
    pass

class CommandError(error):
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
    name = args[0]
    
    if not reloading and name in loaded:
        f.close()
        return False
    
    if reloading:
        reloading = name in loaded
    
    loaded[name] = filename
    
    try:
        imported = imp.load_module(*args)
    finally:
        if not reloading:
            del loaded[name]
        f.close()
    
    if reloading:
        unload(name, True)
    
    loaded[name] = filename
    
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
                register(e_name, e_stage, f_ref, name)
                
                break
    
    return True

# Is the script with the given name loaded?
def is_loaded(s_name):
    name, f, filename, filetype = find_script(s_name)
    f.close()
    
    return name in loaded

# Remove any function which was defined in the given script
def unload(s_name, reloading = False):
    name, f, filename, filetype = find_script(s_name)
    f.close()
    
    if not reloading:
        del loaded[name]

    for e_name in list(events):
        for e_stage in list(events[e_name]):
            to_check = events[e_name][e_stage]
            
            events[e_name][e_stage] = [(f, m) for f, m in to_check if m != name]
            
            if not events[e_name][e_stage]:
                del events[e_name][e_stage]
        
        if not events[e_name]:
            del events[e_name]

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
    name = e.args[0]
    try:
        if load(name):
            raise CommandError("The script is already loaded")
        else:
            e.window.write("* The script '%s' has been loaded." % name)
    except:
        traceback.print_exc()
        raise CommandError("Error loading the script")

def onCommandUnload(e):
    name = e.args[0]
    if is_loaded(name):
        unload(name)
    else:
        raise CommandError("No such script is loaded")

def onCommandReload(e):
    name = e.args[0]
    try:
        load(name, reloading=True)
    except:
        traceback.print_exc()
        raise CommandError("Error loading the script")

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
