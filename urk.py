#!/usr/bin/env python

import imp
import getopt
import sys
import inspect
import os

#add ~/.urk and path (normally where urk.py is located) to sys.path
def path(filename=""):
    urkpath = os.path.dirname(inspect.getfile(sys.modules[__name__]))
    
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath

sys.path = [
    os.path.join(os.path.expanduser("~"), ".urk"),
    os.path.join(os.path.expanduser("~"), ".urk/scripts"),
    ".",
    "./scripts",
    path(),
    path("scripts")
    ] + sys.path

import events
import conf
import ui

name = "urk"
long_name = "urk IRC"
version = 0, -1, 4
long_version = "%s v%s" % (long_name, ".".join(str(x) for x in version))
website = "http://urk.sf.net/"
authors = ["Vincent Povirk", "Marc Liddell"]
copyright = "2005 %s" % ', '.join(authors)

def main():
    for script_path in set(sys.path[1:6:2]):
        try:
            for script in os.listdir(script_path):
                for suffix in imp.get_suffixes():
                    if script.endswith(suffix[0]):
                        events.load(script)
                        break
                    
        except OSError:
            pass

    events.trigger("Start")
    
    ui.start()

if __name__ == "__main__":
    main()
