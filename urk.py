#!/usr/bin/env python

import imp
import getopt
import sys
import inspect
import os

#add ~/.urk and path (normally where urk.py is located) to sys.path
def path(filename=""):
    urkpath = os.path.dirname(inspect.getfile(sys.modules[__name__]))

    return os.path.join(urkpath, filename)

sys.path = [
    os.path.join(os.path.expanduser("~"),".urk"),
    ".",
    path()
    ] + sys.path

import events

opts, dummy = getopt.getopt(sys.argv[1:],'c:u:', ['conf=','ui='])

opts = dict(opts)

conf_module = imp.find_module(opts.get('-c') or opts.get('--conf') or 'conf')
try:
    conf = imp.load_module('conf', *conf_module)
except:
    conf_module[0].close()
    print "Unable to load gconf; your settings will not be saved."
    conf_module = imp.find_module('conf_dummy')
    conf = imp.load_module('conf', *conf_module)
conf_module[0].close()

ui_module = imp.find_module(opts.get('-u') or opts.get('--ui') or 'ui')
ui = imp.load_module('ui', *ui_module)
ui_module[0].close()

name = "urk"
long_name = "urk IRC"
version = 0, -1, 4
long_version = "%s v%s" % (long_name, ".".join(str(x) for x in version))
website = "http://urk.sf.net/"
authors = ["Vincent Povirk", "Marc Liddell"]
copyright = "2005 %s" % ', '.join(authors)
default_scripts = ['theme','chaninfo', 'ctcp', 'irc_script', 'ui_script', 'hotlinking', 'keys']

if __name__ == "__main__":
    for script in conf.get("scripts_to_load") or default_scripts:
        events.load(script)

    events.trigger("Start")
    
    ui.start()
