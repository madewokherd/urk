#!/usr/bin/env python

import gconf

client = gconf.client_get_default()

client.add_dir("/apps/ork",gconf.CLIENT_PRELOAD_ONELEVEL)

def valueToPython(value):
    if value:
        if value.type == gconf.VALUE_STRING:
            data = value.get_string()
            if data.startswith("python:"):
                return eval(data[7:])
            else:
                return data
        elif value.type == gconf.VALUE_INT:
            return value.get_int()
        elif value.type == gconf.VALUE_FLOAT:
            return value.get_float()
        elif value.type == gconf.VALUE_BOOL:
            return value.get_bool()
    else:
        return None

def get(key):
    return valueToPython(client.get("/apps/ork/"+key))

#def onCommandGetconfig(args,window,output,**kwargs):
#    if 'auto' in output:
#        output.remove('auto')
#        window.write(repr(get(args[0])))

def set(key, value):
    key = "/apps/ork/"+key
    setfunctions = {int: client.set_int, float: client.set_float, bool: client.set_bool}    
    if type(value) in setfunctions:
        setfunctions[type(value)](key, value)
    elif type(value) == str and not value.startswith("python:"):
        client.set_string(key, value)
    else:
        client.set_string(key, "python:"+repr(value))

#def onCommandSetconfig(args,window,output,**kwargs):
#    if 'auto' in output:
#        output.remove('auto')
#        set(args[0], eval(' '.join(args[1:])))

class notify:
    def __init__(self, key, function):
        self.key = "/apps/ork/"+key
        self.function = function
        self.notify_id = client.notify_add(key, self.call_function)
    def call_function(self, client, cnxn_id, entry):
        self.function(key, valueToPython(entry.value))
    def stop(self):
        if notify_id: client.notify_remove(notify_id)
        notify_id = False
    def __del__(self):
        self.stop()
