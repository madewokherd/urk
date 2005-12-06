import gtk

import events
import ui
from conf import conf
import urk

class NetworkInfo(gtk.VBox):
    def show(self, network):
        for child in self.get_children():
            self.remove(child)
    
        network_info = conf.get('networks', {}).get(network, {})

        table = gtk.Table(3, 2)
        table.set_row_spacings(3)
        
        # server
        label = gtk.Label('Server:')

        data = gtk.Entry()
        data.set_text(str(network_info.get('server', '')))
        
        def edit(widget, event):
            network_info['server'] = widget.get_text()
                    
        data.connect('key-release-event', edit)

        table.attach(label, 0, 1, 0, 1)
        table.attach(data, 1, 2, 0, 1)
        
        # perform
        label = gtk.Label('Perform:')

        data = gtk.TextView()
        data.get_buffer().set_text(
            '\n'.join(str(p) for p in network_info.get('perform', []))
            )
        
        def edit(widget, event):
            buffer = widget.get_buffer()
            
            perform = buffer.get_text(
                        buffer.get_start_iter(), buffer.get_end_iter()
                        ).split('\n')

            network_info['perform'] = [p for p in perform if p]
                    
        data.connect('key-release-event', edit)

        table.attach(label, 0, 1, 1, 2)
        table.attach(data, 1, 2, 1, 2)

        # autoconnect
        data = gtk.CheckButton(label='Connect on startup')
        data.set_active(network in conf.get('start_networks', []))    
        
        def edit(widget):
            if 'start_networks' not in conf:
                conf['start_networks'] = []

            # note (n in C) != w
            if (network in conf.get('start_networks')) != widget.get_active():
                if widget.get_active():
                    conf.get('start_networks').append(network)
                else:
                    conf.get('start_networks').remove(network)

        data.connect('toggled', edit)    
        
        table.attach(data, 1, 2, 2, 3)
        table.show_all()

        self.add(table)

    def __init__(self):
        gtk.VBox.__init__(self)

class ServerWidget(gtk.VBox):
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
        model, iter = self.networks.get_selection().get_selected()

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
        self.infobox = NetworkInfo()

        network_list = gtk.ListStore(str)
        for network in conf.get('start_networks', []):
             network_list.append([network])
        
        for network in conf.get('networks', []):
            if network not in conf.get('start_networks', []):
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

        self.buttons['connect'].connect('clicked', self.on_connect)

        gtk.VBox.__init__(self)
        self.set_spacing(5)
        
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
        
        self.pack_start(hb)

        self.pack_start(self.infobox, expand=False)
        
        hb = gtk.HButtonBox()
        hb.set_layout(gtk.BUTTONBOX_END)
        
        hb.add(self.buttons['close'])
        hb.add(self.buttons['connect'])
        
        self.pack_end(hb, expand=False)
        
def main():
    w = gtk.Window()
    w.set_title('Connect-o-rama') # XXX replace this
    
    try:
        w.set_icon(
            gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
            )
    except:
        pass

    w.set_default_size(320, 300)
    w.set_border_width(5)
    
    sw = ServerWidget()
    
    def close(button):
        w.destroy()
    
    sw.buttons['close'].connect('clicked', close)
    
    w.add(sw)    
    w.show_all()
        
