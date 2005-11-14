import gtk

import events
import ui
from conf import conf
import urk

class NetworkInfo(gtk.VBox):
    def show_what(self, network_info): 
        keys = ['server', 'perform']
        
        return keys + [k for k in network_info if k not in keys]

    def show(self, network):
        for child in self.get_children():
            self.remove(child)
    
        network_info = conf.get('networks', {}).get(network, {})
        
        to_show = self.show_what(network_info)

        table = gtk.Table(len(to_show), 2)

        for i, key in enumerate(to_show):
            label = gtk.Entry()
            label.set_text(str(key))
            label.show()
            
            value = network_info.get(key, '')
            
            data = gtk.Entry()
            data.set_text(str(value))
            data.show()
            
            def edit(widget, event, key):
                if key == 'perform':
                    try:
                        network_info[key] = eval(widget.get_text())
                    except SyntaxError:
                        pass
                else:
                    network_info[key] = widget.get_text()
            
            data.connect('key-release-event', edit, key)
        
            table.attach(label, 0, 1, i, i+1)
            table.attach(data, 1, 2, i, i+1) 
            
        table.show_all()
        self.add(table)

    def __init__(self):
        gtk.VBox.__init__(self)

class ServerWidget(gtk.Window):
    def edit(self, cell, path_string, new_text, model):
        print ">"
            
    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()
        
        infobox = self.vbox.get_children()[1]
        
        infobox.show(model.get_value(iter, 0))

    def __init__(self, action):
        gtk.Window.__init__(self)
        
        self.set_default_size(320, 300)
        self.set_border_width(5)
        
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(5)
        
        hb = gtk.HBox()
        hb.set_spacing(5)
        
        self.vbox.pack_start(hb)
        self.vbox.pack_start(NetworkInfo(), expand=False)

        #self.ui.get_widget('connect').connect('clicked', connect)

        network_list = gtk.ListStore(str)
        for network in conf.get('networks', []):
            network_list.append([network])

        renderer = gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.edit, network_list)

        networks = gtk.TreeView(network_list)
        networks.set_headers_visible(False)
        networks.insert_column_with_attributes(
            0, '', renderer, text=0
            )
            
        selection = networks.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect('changed', self.on_selection_changed)
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.add(networks)
            
        self.vbox.get_children()[0].pack_start(sw, expand=True)
        
        vb = gtk.VButtonBox()
        vb.set_layout(gtk.BUTTONBOX_START)
        
        button = gtk.Button(stock='gtk-add')
        vb.add(button)
        
        def add_network(button, network_list):
            if 'networks' not in conf:
                conf['networks'] = {}
        
            name = 'NewNetwork'
            
            while name in conf.get('networks'):
                name += '_'

            conf['networks'][name] = {}
            network_list.append([name])
        
        button.connect('clicked', add_network, network_list)

        button = gtk.Button(stock='gtk-remove')
        vb.add(button)
        
        def remove_network(button, network_list):
            model, iter = networks.get_selection().get_selected()

            if iter:
                del conf['networks'][model.get_value(iter, 0)]
                model.remove(iter)
     
        button.connect('clicked', remove_network, network_list)

        self.vbox.get_children()[0].pack_start(vb, expand=False)
        
        hb = gtk.HButtonBox()
        hb.set_layout(gtk.BUTTONBOX_END)
        
        button = gtk.Button(stock='gtk-close')
        hb.add(button)
        
        def close(*args):
            self.destroy()
        
        button.connect('clicked', close)
        
        button = gtk.Button(stock='gtk-connect')
        hb.add(button)
        
        def connect(*args):
            model, iter = self.ui.get_widget('networks').get_selection().get_selected()
            network = model.get_value(iter, 0)
            
            events.run(
                'server %s' % network,
                ui.windows.manager.get_active(),
                ui.windows.manager.get_active().network
                )
                
        button.connect('clicked', connect)
        
        self.vbox.pack_end(hb, expand=False)

        self.add(self.vbox)
        self.show_all()
 
        

        
