import gtk

import events
import ui
from conf import conf
import urk

class NetworkInfo(gtk.VBox):
    def show_what(self, network_info): 
        return ['server', 'perform']

    def show(self, network):
        for child in self.get_children():
            self.remove(child)
    
        network_info = conf.get('networks', {}).get(network, {})
        
        to_show = self.show_what(network_info)

        table = gtk.Table(len(to_show), 2)

        for i, key in enumerate(to_show):
            label = gtk.Label()
            label.set_text('%s:' % str(key).capitalize())
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
    def edit_network(self, cell, path_string, new_text):
        network_list = self.networks.get_model()
    
        networks = conf.get('networks')
        
        if network_list[path_string][0] in networks:
            networks[new_text] = networks.pop(network_list[path_string][0])
        else:
            networks[new_text] = {}

        iter = network_list.get_iter_from_string(path_string)
        network_list.set_value(iter, 0, new_text)
        
    def add_network(self, button):
        network_list = self.networks.get_model()
    
        if 'networks' not in conf:
            conf['networks'] = {}
    
        name = 'NewNetwork'
        
        while name in conf.get('networks'):
            name += '_'

        conf['networks'][name] = {}
        network_list.append([name])
        
    def remove_network(self, button):
        model, iter = networks.get_selection().get_selected()

        if iter:
            del conf['networks'][model.get_value(iter, 0)]
            model.remove(iter)
            
    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()

        if iter:
            self.infobox.show(model.get_value(iter, 0))
            
            self.buttons['connect'].set_sensitive(True)
        else:
            self.buttons['connect'].set_sensitive(False)
            
    def on_close(self, button):
        self.destroy()
        
    def on_connect(self, button):
        model, iter = self.networks.get_selection().get_selected()
        
        if iter:
            network = model.get_value(iter, 0)
            
            events.run(
                'server %s' % network,
                ui.windows.manager.get_active(),
                ui.windows.manager.get_active().network
                )

    def __init__(self):
        gtk.Window.__init__(self)
        
        self.set_default_size(320, 300)
        self.set_border_width(5)

        self.infobox = NetworkInfo()

        network_list = gtk.ListStore(str)
        for network in conf.get('networks', []):
            network_list.append([network])

        renderer = gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.edit_network)

        self.networks = gtk.TreeView(network_list)
        self.networks.set_headers_visible(False)
        self.networks.insert_column_with_attributes(
            0, '', renderer, text=0
            )
            
        selection = self.networks.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect('changed', self.on_selection_changed)

        self.buttons = {
            'add': gtk.Button(stock='gtk-add'),
            'remove': gtk.Button(stock='gtk-remove'),
            
            'close': gtk.Button(stock='gtk-close'),
            'connect': gtk.Button(stock='gtk-connect'),
            }
        
        self.buttons['add'].connect('clicked', self.add_network)
        self.buttons['remove'].connect('clicked', self.remove_network)

        self.buttons['close'].connect('clicked', self.on_close)
        self.buttons['connect'].connect('clicked', self.on_connect)

        vbox = gtk.VBox()
        vbox.set_spacing(5)
        
        hb = gtk.HBox()
        hb.set_spacing(5)

        vb = gtk.VButtonBox()
        vb.set_layout(gtk.BUTTONBOX_START)
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.add(self.networks)
        
        vb.add(self.buttons['add'])
        vb.add(self.buttons['remove'])
        
        hb.pack_start(sw, expand=True)
        hb.pack_start(vb, expand=False)
        
        vbox.pack_start(hb)

        vbox.pack_start(self.infobox, expand=False)
        
        hb = gtk.HButtonBox()
        hb.set_layout(gtk.BUTTONBOX_END)
        
        hb.add(self.buttons['close'])
        hb.add(self.buttons['connect'])
        
        vbox.pack_end(hb, expand=False)

        self.add(vbox)
        self.show_all()
 
        

        
