import events
import conf
import ui

name = "Urk"
long_name = "Urk IRC Client"
version = "0.-1.2"
long_version = "%s v%s" % (long_name, version)
website = "http://urk.sf.net/"
authors = ["Vincent Povirk", "Marc Liddell"]
copyright = "2005 %s" % ', '.join(authors)

if __name__ == "__main__":
    for script in conf.get("scripts_to_load") or ['script.py','theme.py','irc_basicinfo.py', 'irc_events_us.py']:
        events.load(script)

    events.trigger("Start")
    
    ui.start()
