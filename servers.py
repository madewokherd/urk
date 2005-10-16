import gtk
import gtk.glade
from conf import conf
import __main__ as urk

class ServerWidget(gtk.Window):
    def __init__(self, action):
        ui = gtk.glade.XML(urk.path("servers.glade"))

        network_list = gtk.ListStore(str)
        
        combobox = ui.get_widget("network_list")
        combobox.set_model(network_list)
        
        cell = gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)
        
        for network in conf["networks"]:
            if network.endswith("/"):
                network_list.append([network[:-1]])
                
        combobox.set_active(len(combobox) - 1)
