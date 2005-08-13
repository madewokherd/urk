import events
import conf
import ui

get_window = {}

def connect(network):
    for window in ui.tabs:
        if window.type == "first_window":
            window.title = network.server
            ui.tabs.get_tab_label(window).update_label()
            break
    else:
        window = ui.IrcWindow(network, 'status', "Status Window", network.server)
        ui.new_tab(window, network)

    window.network = network  
    window.type = "status" 

    ui.activate(window)

    get_window[network] = window

if __name__ == "__main__":
    for script in (conf.get("scripts_to_load") or ['script.py','theme.py','irc_basicinfo.py', 'irc_events_us.py']):
        events.load(script)

    events.trigger("Start")
    
    ui.start()
