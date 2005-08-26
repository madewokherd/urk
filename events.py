import sys
import os
import traceback

class data:
    done = False
    quiet = False
    
    def __init__(self, **kwargs):
        for attr in kwargs.items():
            setattr(self, *attr)

class getdict(object):
    __slots__ = ['__weakref__', 'target']
    
    def __init__(self, target):
        self.target = target
    
    def __getitem__(self, name):
        return getattr(self.target, name)

trigger_sequence = ("setup", "pre", "def", "on", "post")

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
                    except:
                        traceback.print_exc()

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
def load(s_name, reloading=False):
    # split the directory and filename
    dirname = os.path.dirname(filename)
    filename = os.path.basename(filename)
    
    # FIXME: how do we import without adding evil paths to our sys.path?
    # add our path if it's not there
    in_path = True
    
    if dirname not in sys.path:
        sys.path.append(dirname)
        in_path = False
    
    if filename.endswith(".py"):
        filename = filename[:-3]
    
    imported = __import__(filename)
    
    if reloading:
        reload(imported)
    
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

def refresh(s_name):
    unload(s_name)
    load(s_name, reloading=True)
