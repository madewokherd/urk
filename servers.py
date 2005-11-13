import gtk
import gtk.glade

import events
import ui
from conf import conf
import urk

class ServerWidget(gtk.Window):
    def edit(self, cell, path_string, new_text, model):
        print ">"

    def select_network(self, widget, event):
        infobox = self.ui.get_widget('infobox')
        
        for child in infobox.get_children():
            infobox.remove(child)
            
        x, y = event.get_coords()
        x, y = int(x), int(y)
    
        (data,), path, x, y = self.ui.get_widget('networks').get_path_at_pos(x, y)
        
        network = self.ui.get_widget('networks').get_model()[data][0]
            
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
            
        networks = self.ui.get_widget('networks')
        
        networks.connect("button-press-event", self.select_network)
        
        networks.set_headers_visible(False)

        network_list = gtk.ListStore(str)
        networks.set_model(network_list)
        
        renderer = gtk.CellRendererText()
        renderer.connect('edited', self.edit)
        
        networks.insert_column_with_attributes(
            0, "", renderer, text=0
            )

        for network in conf.get('networks', []):
            network_list.append([network])
