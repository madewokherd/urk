import events
import conf

# FIXME, do this properly... whatever that means
get_network = {}
get_window = {}

def connect(network):
    # FIXME, we prolly need lots of code here to do stuff
    #        like check if we actually managed to connect and such,
    #        possibly not though since we definitely have a window, since we
    #        even attempted to connect
    
    # FIXME, somewhere there needs to be an elaborate data
    #        structure mapping channel windows to their network
    
    network_window = ui.IrcWindow(network.fullname)
    
    ui.ui.new_tab(network_window, network)
    
    get_network[network_window] = network
    get_window[network] = network_window
    
    network.connect()

if __name__ == "__main__":
    import irc

    scripts_to_load = conf.get("scripts_to_load")
    for script in scripts_to_load:
        events.load(script)

    import ui
    
    events.trigger("Start")
    
    ui.start()
