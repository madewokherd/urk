import sys
import os

class data:
    def __init__(self, **kwargs):
        for attr in kwargs.items():
            setattr(self, *attr)

trigger_sequence = ("setup", "pre", "on", "post")

events = {}

# An event has occurred, the e_name event!
def trigger(e_name, e_data=None):
    if e_name in events:
        event_f = events[e_name]
    
        for t in trigger_sequence:
            if t in event_f:
                for f_ref, s_name in event_f[t]:
                    try:
                        f_ref(e_data)
                    except Exception, e:
                        print f_ref.__name__, e_data, e
    
def dir_and_file(filename):
    d = os.path.dirname(filename)
    f = os.path.basename(filename)
    
    return d, f

# Registers a specific function with an event at the given sequence stage.
def register(e_name, e_stage, f_ref, s_name=""):
    if e_name in events:
        if e_stage in events[e_name]:
            events[e_name][e_stage] += [(f_ref, s_name)]
        else:
            events[e_name][e_stage] = [(f_ref, s_name)]
    else:
        events[e_name] = {e_stage: [(f_ref, s_name)]}

# Load a python script and register
# the functions defined in it for events.
def load(s_name):
    # split the directory and filename
    dirname, filename = dir_and_file(s_name)
    
    # FIXME, how do we import without adding evil paths to our sys.path?
    # add our path if it's not there
    in_path = True
    
    if dirname not in sys.path:
        sys.path.append(dirname)
        in_path = False

    imported = __import__(filename.strip(".py"))
    
    if not in_path:
        sys.path.remove(dirname)
    
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
                register(e_name, e_stage, f_ref, s_name)
                    
# Remove any function which was defined in the given script
def unload(s_name):
    for e_name in events:
        for t in events[e_name]:
            to_check = events[e_name][t]
        
            events[e_name][t] = [(f, m) for f, m in to_check if m != s_name]
