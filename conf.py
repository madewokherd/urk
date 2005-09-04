import gconf

client = gconf.client_get_default()

client.add_dir("/apps/urk",gconf.CLIENT_PRELOAD_ONELEVEL)

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
    gconf_key = "/apps/urk/"+key
    if gconf_key.endswith('/'):
        result = {}
        for entry in client.all_entries(gconf_key[:-1]):
            result[entry.key[len(gconf_key):]] = valueToPython(entry.get_value())
        for directory in client.all_dirs(gconf_key[:-1]):
            result[directory[len(gconf_key):]+'/'] = get(directory[10:]+'/')
        return result
    else:
        return valueToPython(client.get("/apps/urk/"+key))

def set(key, value):
    key = "/apps/urk/"+key

    setfunctions = {
        int: client.set_int, 
        float: client.set_float, 
        bool: client.set_bool
        }

    if type(value) in setfunctions:
        setfunctions[type(value)](key, value)
    elif isinstance(value, str) and not value.startswith("python:"):
        client.set_string(key, value)
    else:
        client.set_string(key, "python:"+repr(value))

class notify:
    def __init__(self, key, function):
        self.key = "/apps/urk/"+key
        self.function = function
        self.notify_id = client.notify_add(key, self.call_function)
    def call_function(self, client, cnxn_id, entry):
        self.function(key, valueToPython(entry.value))
    def stop(self):
        if notify_id: client.notify_remove(notify_id)
        notify_id = False
    def __del__(self):
        self.stop()
