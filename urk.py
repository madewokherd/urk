import events
import conf
import ui

get_window = {}

def connect(network):
    if ui.ui.tabs.get_n_pages() == 1 and not ui.ui.tabs.get_nth_page(0).get_data("network"):
        network_window = ui.ui.tabs.get_nth_page(0)
        network_window.set_data('network', network)
        ui.ui.tabs.set_tab_label_text(network_window, network.server)
    else:
        network_window = ui.IrcWindow(network.server)
        network_window.type = "status"
        ui.new_tab(network_window, network) 
           
    ui.activate(network_window)
    
    get_window[network] = network_window

    #network.connect()

if __name__ == "__main__":
    for script in conf.get("scripts_to_load"):
        events.load(script)

    events.trigger("Start")
    
    ui.start()
