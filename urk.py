import events
import conf
import ui

get_window = {}

def connect(network):
    network_window = ui.IrcWindow(network.fullname)
    
    ui.new_tab(network_window, network)    
    ui.activate(network_window)
    
    get_window[network] = network_window

    network.connect()

if __name__ == "__main__":
    for script in conf.get("scripts_to_load"):
        events.load(script)

    events.trigger("Start")
    
    ui.start()
