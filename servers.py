import gtk
import gtk.glade
import conf

class ServerWidget(gtk.Window):
    def __init__(self, action):
        ui = gtk.glade.XML("servers.glade")

        network_list = gtk.ListStore(str)
        
        combobox = ui.get_widget("network_list")
        combobox.set_model(network_list)
        
        cell = gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)
        
        for network in conf.get("networks/"):
            if network.endswith("/"):
                network_list.append([network[:-1]])
                
        combobox.set_active(len(combobox) - 1)
