import events
import conf
import ui

get_window = {}

def connect(network):
    if ui.tabs.get_n_pages() and ui.tabs.get_nth_page(0).type == "first_window":
        network_window = ui.tabs.get_nth_page(0)
        ui.tabs.set_tab_label_text(network_window, network.server)
    else:
        network_window = ui.IrcWindow(network.server)
        ui.new_tab(network_window, network)

    network_window.network = network  
    network_window.type = "status" 
           
    ui.activate(network_window)
    
    get_window[network] = network_window

    #network.connect()

if __name__ == "__main__":
    for script in conf.get("scripts_to_load"):
        events.load(script)

    events.trigger("Start")
    
    ui.start()
