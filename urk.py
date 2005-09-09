#!/usr/bin/env python

import imp
import getopt
import sys
import inspect
import os

#add ~/.urk and urk_path (normally where urk.py is located) to sys.path
urk_path = None #change this line when we do a system install
if not urk_path: #normal install
    urk_path = os.path.dirname(inspect.getfile(sys.modules[__name__]))

sys.path = [os.path.expanduser("~/.urk"),".",urk_path] + sys.path

import events

opts, dummy = getopt.getopt(sys.argv[1:],'c:u:', ['conf=','ui='])

opts = dict(opts)

conf_module = imp.find_module(opts.get('-c') or opts.get('--conf') or 'conf')
conf = imp.load_module('conf', *conf_module)
conf_module[0].close()

ui_module = imp.find_module(opts.get('-u') or opts.get('--ui') or 'ui')
ui = imp.load_module('ui', *ui_module)
ui_module[0].close()

name = "Urk"
long_name = "Urk IRC Client"
version = 0, -1, 2
long_version = "%s v%s" % (long_name, ".".join(str(x) for x in version))
website = "http://urk.sf.net/"
authors = ["Vincent Povirk", "Marc Liddell"]
copyright = "2005 %s" % ', '.join(authors)

if __name__ == "__main__":
    for script in conf.get("scripts_to_load") or ['script.py','theme.py','irc_basicinfo.py', 'irc_events_us.py']:
        events.load(script)

    events.trigger("Start")
    
    ui.start()
