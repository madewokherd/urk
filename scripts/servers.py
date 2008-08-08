import gc

import gtk

import events
import windows
from conf import conf
import urk

if 'networks' not in conf:
    conf['networks'] = {}

def server_get_data(network_info):
    if 'port' in network_info:
        return "%s:%s" % (
            network_info.get('server', '') , network_info.get('port')
            )
    else:
        return network_info.get('server', '')
        
def server_set_data(text, network_info):
    if ':' in text:
        network_info['server'], port = text.rsplit(':',1)
        network_info['port'] = int(port)
    else:
        network_info['server'] = text
        network_info.pop('port', None)
            
def channels_get_data(network_info):
    return '\n'.join(network_info.get('join', ()))
            
def channels_set_data(text, network_info):
    network_info['join'] = []
    
    for line in text.split('\n'):
        for chan in line.split(','):
            if chan:
                network_info['join'].append(chan.strip())
    
def perform_get_data(network_info):
    return '\n'.join(network_info.get('perform', ()))
            
def perform_set_data(text, network_info):
    network_info['perform'] = [line for line in text.split('\n') if line]
    
def autoconnect_set_data(do_autoconnect, network): 
    if 'start_networks' not in conf:
        conf['start_networks'] = []

    # note (n in C) != w
    if (network in conf.get('start_networks')) != do_autoconnect:
        if do_autoconnect:
            conf.get('start_networks').append(network)
        else:
            conf.get('start_networks').remove(network)

class NetworkInfo(gtk.Frame):
    def update(self):
        for child in self.get_children():
            self.remove(child)
    
        network_info = conf.get('networks', {}).get(self.network, {})

        table = gtk.Table(4, 2)
        table.set_row_spacings(3)
        
        # server
        label = gtk.Label('Server:')

        data = gtk.Entry()
        data.set_text(server_get_data(network_info))
        data.connect(
            'key-release-event', 
            lambda w, e: server_set_data(w.get_text(), network_info)
            )

        table.attach(label, 0, 1, 0, 1, xoptions=gtk.FILL)
        table.attach(data, 1, 2, 0, 1, xoptions=gtk.FILL)
        
        def get_text_from_textview(textview):
            buffer = textview.get_buffer()
            return buffer.get_text(
                buffer.get_start_iter(), buffer.get_end_iter()
                )
        
        # channels
        label = gtk.Label('Channels:')

        data = gtk.TextView()
        data.get_buffer().set_text(channels_get_data(network_info))
        data.connect(
            'key-release-event', 
            lambda w, e: channels_set_data(get_text_from_textview(w), network_info)
            )

        table.attach(label, 0, 1, 1, 2, xoptions=gtk.FILL)
        table.attach(data, 1, 2, 1, 2, xoptions=gtk.FILL)
        
        # perform
        label = gtk.Label('Perform:')

        data = gtk.TextView()
        data.get_buffer().set_text(perform_get_data(network_info))
        data.connect(
            'key-release-event',
            lambda w, e: perform_set_data(get_text_from_textview(w), network_info)
            )

        table.attach(label, 0, 1, 2, 3, xoptions=gtk.FILL)
        table.attach(data, 1, 2, 2, 3, xoptions=gtk.FILL)

        # autoconnect
        data = gtk.CheckButton(label='Connect on startup')
        data.set_active(self.network in conf.get('start_networks', []))  
        data.connect(
            'toggled',
            lambda w: autoconnect_set_data(w.get_active(), self.network)
            )  
        
        table.attach(data, 1, 2, 3, 4, xoptions=gtk.FILL)

        box = gtk.HBox()
        box.pack_start(table, padding=5)
        self.add(box)
        
        self.set_label(self.network)
        self.show_all()

class ServerWidget(gtk.VBox):
    def edit_network(self, cell, path_string, new_text):
        network_list = self.networks.get_model()
        old_text = network_list[path_string][0]
        
        networks = conf.get('networks')
        networks[new_text] = networks.pop(old_text, {})

        start_networks = conf.get('start_networks', [])
        if old_text in start_networks:
            start_networks[start_networks.index(old_text)] = new_text

        iter = network_list.get_iter_from_string(path_string)
        network_list.set_value(iter, 0, new_text)

        self.infobox.network = new_text
        
    def add_network(self, button):
        name = 'NewNetwork'
        while name in conf.get('networks'):
            name += '_'

        conf['networks'][name] = {}
        network_list = self.networks.get_model()
        path = network_list.append([name])
        
        # presumably we're meant to use the thing append returns but that
        # doesn't work
        path = (len(network_list)-1)

        self.networks.set_cursor(
            path,
            focus_column=self.networks.get_column(0),
            start_editing=True
            )
        
    def remove_network(self, button):
        model, iter = self.networks.get_selection().get_selected()

        if iter:
            name = model.get_value(iter, 0)
            if name in conf.get('start_networks', ()):
                conf['start_networks'].remove(name)
            del conf['networks'][name]
            model.remove(iter)
            
        if len(model):
            self.networks.set_cursor((len(model)-1,))
            
    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()

        if iter:
            self.infobox.network = model.get_value(iter, 0)
            self.infobox.update()
            
            self.buttons['connect'].set_sensitive(True)
        else:
            self.buttons['connect'].set_sensitive(False)
        
    def on_connect(self, button):
        model, iter = self.networks.get_selection().get_selected()
        
        if iter:
            network_name = model.get_value(iter, 0)
            window = windows.manager.get_active()
            network = window.network
            
            if network and network.status:
                switches = 'm'
            else:
                switches = ''
            
            events.run(
                'server -%s %s' % (switches, network_name),
                window,
                network
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
        
        serverlist = gtk.VBox()
        serverlist.set_spacing(5)

        serverlist_buttons = gtk.HButtonBox()
        serverlist_buttons.set_layout(gtk.BUTTONBOX_START)
        
        serverlist_window = gtk.ScrolledWindow()
        serverlist_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        serverlist_window.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        serverlist_window.add(self.networks)
        
        serverlist_buttons.add(self.buttons['add'])
        serverlist_buttons.add(self.buttons['remove'])
        
        serverlist.pack_start(serverlist_window, expand=True)
        serverlist.pack_start(serverlist_buttons, expand=False)
        
        hb = gtk.HBox()
        hb.set_spacing(5)
        hb.pack_start(serverlist, expand=False)
        hb.pack_start(self.infobox)
        
        self.pack_start(hb)
        
        hb = gtk.HButtonBox()
        hb.set_layout(gtk.BUTTONBOX_END)
        
        hb.add(self.buttons['close'])
        hb.add(self.buttons['connect'])
        
        self.pack_end(hb, expand=False)

def main():
    gc.collect()

    win = gtk.Window()
    win.set_title('Connect-o-rama') # XXX replace this
    
    try:
        w.set_icon(
            gtk.gdk.pixbuf_new_from_file(urk.path("urk_icon.svg"))
            )
    except:
        pass

    win.set_default_size(320, 300)
    win.set_border_width(5)
    
    widget = ServerWidget()
    
    def close(button):
        win.destroy()
    
    widget.buttons['close'].connect('clicked', close)
    
    win.add(widget)    
    win.show_all()

def setupMainMenu(e):
    e.menu += [('Servers', gtk.STOCK_CONNECT, main)]

