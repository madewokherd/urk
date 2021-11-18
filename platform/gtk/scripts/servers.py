import gc

from gi.repository import Gtk

import events
import windows
from conf import conf
import ui
import urk

if 'networks' not in conf:
    conf['networks'] = {}

_save_config_source = None

def save_config():
    global _save_config_source
    import conf
    if _save_config_source:
        _save_config_source.unregister()
    _save_config_source = ui.register_timer(3000, conf.save)

def server_get_data(network_info):
    if network_info.get('ssl', None):
        return "%s:+%s" % (
            network_info.get('server', '') , network_info.get('port', 6697)
            )
    if 'port' in network_info:
        return "%s:%s" % (
            network_info.get('server', '') , network_info.get('port')
            )
    return network_info.get('server', '')
        
def server_set_data(text, network_info):
    if ':' in text:
        network_info['server'], port = text.rsplit(':',1)
        if port.startswith('+'):
            network_info['ssl'] = True
            port = port[1:]
        else:
            network_info['ssl'] = None
        network_info['port'] = int(port)
    else:
        network_info['server'] = text
        network_info.pop('port', None)
    save_config()
            
def channels_get_data(network_info):
    return '\n'.join(network_info.get('join', ()))
            
def channels_set_data(text, network_info):
    network_info['join'] = []
    
    for line in text.split('\n'):
        for chan in line.split(','):
            if chan:
                network_info['join'].append(chan.strip())
    save_config()
    
def perform_get_data(network_info):
    return '\n'.join(network_info.get('perform', ()))
            
def perform_set_data(text, network_info):
    network_info['perform'] = [line for line in text.split('\n') if line]
    save_config()
    
def autoconnect_set_data(do_autoconnect, network): 
    if 'start_networks' not in conf:
        conf['start_networks'] = []

    # note (n in C) != w
    if (network in conf.get('start_networks')) != do_autoconnect:
        if do_autoconnect:
            conf.get('start_networks').append(network)
        else:
            conf.get('start_networks').remove(network)
    save_config()

class NetworkInfo(Gtk.Frame):
    def update(self):
        for child in self.get_children():
            self.remove(child)
    
        network_info = conf.get('networks', {}).get(self.network, {})

        table = Gtk.Table(4, 2)
        table.set_row_spacings(3)
        
        # server
        label = Gtk.Label(label='Server:')

        data = Gtk.Entry()
        data.set_text(server_get_data(network_info))
        data.connect(
            'key-release-event', 
            lambda w, e: server_set_data(w.get_text(), network_info)
            )

        table.attach(label, 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL)
        table.attach(data, 1, 2, 0, 1, xoptions=Gtk.AttachOptions.FILL)
        
        def get_text_from_textview(textview):
            buffer = textview.get_buffer()
            return buffer.get_text(
                buffer.get_start_iter(), buffer.get_end_iter()
                )
        
        # channels
        label = Gtk.Label(label='Channels:')

        data = Gtk.TextView()
        data.get_buffer().set_text(channels_get_data(network_info))
        data.connect(
            'key-release-event', 
            lambda w, e: channels_set_data(get_text_from_textview(w), network_info)
            )

        table.attach(label, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)
        table.attach(data, 1, 2, 1, 2, xoptions=Gtk.AttachOptions.FILL)
        
        # perform
        label = Gtk.Label(label='Perform:')

        data = Gtk.TextView()
        data.get_buffer().set_text(perform_get_data(network_info))
        data.connect(
            'key-release-event',
            lambda w, e: perform_set_data(get_text_from_textview(w), network_info)
            )

        table.attach(label, 0, 1, 2, 3, xoptions=Gtk.AttachOptions.FILL)
        table.attach(data, 1, 2, 2, 3, xoptions=Gtk.AttachOptions.FILL)

        # autoconnect
        data = Gtk.CheckButton(label='Connect on startup')
        data.set_active(self.network in conf.get('start_networks', []))  
        data.connect(
            'toggled',
            lambda w: autoconnect_set_data(w.get_active(), self.network)
            )  
        
        table.attach(data, 1, 2, 3, 4, xoptions=Gtk.AttachOptions.FILL)

        box = Gtk.HBox()
        box.pack_start(table, True, True, 5)
        self.add(box)
        
        self.set_label(self.network)
        self.show_all()

class ServerWidget(Gtk.VBox):
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
        save_config()
        
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
            save_config()
            
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

        network_list = Gtk.ListStore(str)
        for network in conf.get('start_networks', []):
             network_list.append([network])
        
        for network in conf.get('networks', []):
            if network not in conf.get('start_networks', []):
                network_list.append([network])

        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect('edited', self.edit_network)

        self.networks = Gtk.TreeView(network_list)
        self.networks.set_headers_visible(False)
        self.networks.insert_column_with_attributes(
            0, '', renderer, text=0
            )
            
        selection = self.networks.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect('changed', self.on_selection_changed)

        self.buttons = {
            'add': Gtk.Button(stock='gtk-add'),
            'remove': Gtk.Button(stock='gtk-remove'),
            
            'close': Gtk.Button(stock='gtk-close'),
            'connect': Gtk.Button(stock='gtk-connect'),
            }
        
        self.buttons['add'].connect('clicked', self.add_network)
        self.buttons['remove'].connect('clicked', self.remove_network)

        self.buttons['connect'].connect('clicked', self.on_connect)

        GObject.GObject.__init__(self)
        self.set_spacing(5)
        
        serverlist = Gtk.VBox()
        serverlist.set_spacing(5)

        serverlist_buttons = Gtk.HButtonBox()
        serverlist_buttons.set_layout(Gtk.ButtonBoxStyle.START)
        
        serverlist_window = Gtk.ScrolledWindow()
        serverlist_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        serverlist_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        serverlist_window.add(self.networks)
        
        serverlist_buttons.add(self.buttons['add'])
        serverlist_buttons.add(self.buttons['remove'])
        
        serverlist.pack_start(serverlist_window, True, True, 0)
        serverlist.pack_start(serverlist_buttons, False, True, 0)
        
        hb = Gtk.HBox()
        hb.set_spacing(5)
        hb.pack_start(serverlist, False, True, 0)
        hb.pack_start(self.infobox, True, True, 0)
        
        self.pack_start(hb, True, True, 0)
        
        hb = Gtk.HButtonBox()
        hb.set_layout(Gtk.ButtonBoxStyle.END)
        
        hb.add(self.buttons['close'])
        hb.add(self.buttons['connect'])
        
        self.pack_end(hb, False, True, 0)

def main():
    gc.collect()

    win = Gtk.Window()
    win.set_title('Networks')
    
    try:
        w.set_icon(
            GdkPixbuf.Pixbuf.new_from_file(urk.path("urk_icon.svg"))
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
    e.menu += [('Manage Networks', main)]

