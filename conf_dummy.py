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

def get(key):
    return values.get(key)

def set(key, value):
    values[key] = value
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
