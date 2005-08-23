import events
import conf
import ui

get_window = {}

def connect(network):
    window = ui.make_window(network, 'status', "Status Window", "[%s]" % network.server)
    ui.activate(window)

    get_window[network] = window

if __name__ == "__main__":
    for script in conf.get("scripts_to_load") or ['script.py','theme.py','irc_basicinfo.py', 'irc_events_us.py']:
        events.load(script)

    events.trigger("Start")
    
    ui.start()
