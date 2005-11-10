#!/usr/bin/python -O

import imp
import os
import sys

sys.modules['urk'] = sys.modules[__name__]

#add ~/.urk and path (normally where urk.py is located) to sys.path
urkpath = os.path.dirname(__file__)
def path(filename=""):
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath

if os.access(path('profile'),os.F_OK) or os.path.expanduser("~") == "~":
    userpath = path('profile')
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'))
else:
    userpath = os.path.join(os.path.expanduser("~"), ".urk")
    if not os.access(userpath,os.F_OK):
        os.mkdir(userpath, 0700)
    if not os.access(os.path.join(userpath,'scripts'),os.F_OK):
        os.mkdir(os.path.join(userpath,'scripts'), 0700)

sys.path = [
    userpath,
    os.path.join(userpath, "scripts"),
    os.curdir,
    os.path.join(os.curdir, "scripts"),
    path(),
    path("scripts")
    ] + sys.path

import events
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

    ui.start()

if __name__ == "__main__":
    main()
