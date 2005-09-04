#dummy conf module that doesn't save settings across sessions

#this is mostly here so developers can simulate a fresh install, but users can
#use it as a substitute for the normal conf.py, which requires gnome-python

#to simply use urk with no default settings, run 'python urk.py -c conf_dummy'

#the initial settings; you should make a copy if you want to change these
values = {
    #'setting-name': python-expression,
    #'setting-name': python-expression,
    }


import weakref

notify_objects = weakref.WeakKeyDictionary()

def get(key, value_dict = None):
    if value_dict is None:
        value_dict = values
    if key == '':
        return value_dict
    elif '/' in key:
        directory, setting = key.split('/',1)
        directory += '/'
        if directory in value_dict:
            return get(setting, value_dict[directory])
        else:
            return get(setting, {})
    else:
        return value_dict.get(key)

def _set(key, value, value_dict):
    if '/' in key:
        directory, setting = key.split('/',1)
        directory += '/'
        if directory not in value_dict:
            value_dict[directory] = {}
        _set(setting, value, value_dict[directory])
    else:
        value_dict[key] = value

def set(key, value):
    _set(key, value, values)
    for n in notify_objects:
        if n.key == key:
            n.function(value)

class notify:
    def __init__(self, key, function):
        self.key = key
        self.function = function
        notify_objects[self] = None
    def stop(self):
        try:
            del notify_objects[self]
        except KeyError:
            return
