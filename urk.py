import events
import conf
import ui

get_window = {}

def connect(network):
    if ui.tabs.get_n_pages() and ui.tabs.get_nth_page(0).type == "first_window":
        window = ui.tabs.get_nth_page(0)
        window.title = network.server
        ui.fix_tab_label(window)

    else:
        window = ui.IrcWindow(network.server)
        ui.new_tab(window, network)

    window.network = network  
    window.type = "status" 
           
    ui.activate(window)
    
    get_window[network] = window

if __name__ == "__main__":
    for script in conf.get("scripts_to_load"):
        events.load(script)

    events.trigger("Start")
    
    ui.start()
