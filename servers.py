import gtk
import gtk.glade

import events
import ui
from conf import conf
import urk

class ServerWidget(gtk.Window):
    def select_network(self, widget):
        infobox = self.ui.get_widget('infobox')
        
        for child in infobox.children():
            infobox.remove(child)
            
        active = self.ui.get_widget('networks').get_active()
        
        network = self.ui.get_widget('networks').get_model()[active][0]
            
        network_info = conf.get('networks', {}).get(network, {})
      
        for key, value in network_info.items():
            label = gtk.Label(str(key))
            label.show()
            
            data = gtk.Entry()
            data.set_text(str(value))
            data.show()
            
            def edit(widget, event, key):
                network_info[key] = widget.get_text()
            
            data.connect('key-release-event', edit, key)
        
            infobox.add(label)
            infobox.add(data)

    def __init__(self, action):
        self.ui = gtk.glade.XML(urk.path('servers.glade'))
        
        def connect(widget):
            active = self.ui.get_widget('networks').get_active()
            network = self.ui.get_widget('networks').get_model()[active][0]
            
            events.run(
                'server %s' % network,
                ui.windows.manager.get_active(),
                ui.windows.manager.get_active().network
                )
            
        self.ui.get_widget('connect').connect('clicked', connect)
            
        combobox = self.ui.get_widget('networks')

        network_list = gtk.ListStore(str)
        
        combobox = self.ui.get_widget('networks')
        combobox.set_model(network_list)
        
        combobox.connect('changed', self.select_network)
        
        cell = gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)
        
        for network in conf.get('networks', []):
            network_list.append([network])
                
        combobox.set_active(len(combobox) - 1)
