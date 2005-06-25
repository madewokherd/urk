import events
import __main__ as urk
import ui

command_char = "/"

def setupInput(event):
    if not hasattr(event, 'actions'):
        event.actions = set()
        
    if event.text[0] == command_char:
        event.actions.add('command')
        event.command = event.text[1:]
    else:
        event.actions.add('default')

def onInput(event):
    if 'command' in event.actions:
        split = event.command.split()
        e_data = events.data()
        e_data.name = split[0]
        e_data.args = split[1:]
        e_data.text = event.command
        e_data.window = event.window
        e_data.network = event.network
        events.trigger('Command', e_data)
        if 'default' in e_data.actions:
            event.window.write('Unknown command: '+e_data.name)
        event.actions.remove('command')

#should this be something like onCommandEcho?
#if so, how?
def handle_echo(event):
    event.window.write(' '.join(event.args))

def handle_query(event):
    target = event.network.user(event.args[0])
    if target.window:
        #FIXME: select the window
        pass
    else:
        window = ui.IrcWindow(str(target))
           # str so if we say /query byte and we see Byte, we query Byte
        window.set_data('type', 'query')
        window.set_data('target', target)
        target.window = window
        ui.ui.new_tab(target.window, event.network)

def handle_raw(event):
    if event.network.connected:
        event.network.raw(' '.join(event.args))
    else:
        event.window.write("* /raw: We're not connected.")

def handle_join(event):
    if not event.args:
        event.window.write("* /join: You must supply a channel.")
    elif not event.network.connected:
        event.window.write("* /join: We're not connected.")
    else:
        # FIXME: We might want to activate tabs for channels we /joined
        event.network.join(event.args[0])

command_handlers = {
    'echo': handle_echo,
    'query': handle_query,
    'raw': handle_raw,
    'quote': handle_raw,
    'join': handle_join,
}

def setupCommand(event):
    if not hasattr(event, 'actions'):
        event.actions = set(['default'])

def onCommand(event):
    if 'default' in event.actions and event.name in command_handlers:
        command_handlers[event.name](event)
        event.actions.remove('default')

def postCommand(event):
    if 'default' in event.actions and event.network.connected:
        event.network.raw(event.text)
        event.actions.remove('default')

# FIXME, find a list of networks to join from somewhere, prolly conf
#         then join them
def start_networks():
    return []

def onStart(event):
    on_start_networks = start_networks()

    for network in on_start_networks:
        # FIXME, given a network, might we want to look up servers?, possibly 
        #        this should happen on instantiation of the Network() otherwise
        #        i guess it should be done whenever we need to connect to a
        #        network, ie. here and some other places
        urk.connect(network)
        
def onConnectArlottOrg(event):
    import irc, conf

    x = irc.Network("irc.arlott.org", conf.get("nick"), "blackhole.arlott.org")
    
    urk.connect(x)

def onRaw(event):
    if event.msg[1] == "PING":
        event.network.raw("PONG :%s" % event.msg[-1])
    
    e_data = events.data()
    e_data.msg = event.msg
    e_data.rawmsg = event.rawmsg
    e_data.source = event.source
    
    if event.msg[1] == "JOIN":
        e_data.channel = event.network.channel(event.msg[2])
        e_data.target = e_data.channel
        events.trigger('Join', e_data)
    
    event.window.write(event.rawmsg)
        
def onSocketConnect(event):
    import conf

    event.network.raw("NICK %s" % conf.get("nick"))
    event.network.raw("USER %s %s %s :%s" % ("a", "b", "c", "MrUrk"))

def setupDisconnect(event):
    if not hasattr(event, 'window'):
        event.window = urk.get_window[event.network]
    if not hasattr(event, 'actions'):
        event.actions = set(['default'])

def onDisconnect(event):
    if 'default' in event.actions:
        if event.error:
            print event.error
        event.window.write('* Disconnected')
        event.actions.remove('default')

def setupNewChannelWindow(event):
    if not hasattr(event, 'actions'):
        event.actions = set(['default'])
    else:
        event.actions.add('default')
    #FIXME: This should be 'virtual' if we don't want to make a new window
    # and onNewChannelWindow should handle it.

def onNewChannelWindow(event):
    if 'default' in event.actions:
        window = ui.IrcChannelWindow(str(event.channel))
        event.channel.window = window
        event.window = window
        window.set_data('type', 'channel')
        window.set_data('target', event.channel)
        ui.ui.new_tab(window, event.channel.network)
        event.actions.remove('default')

def setupJoin(event):
    if not hasattr(event, 'actions'):
        event.actions = set(['default'])
    else:
        event.actions.add('default')

    event.window = ui.getChannelWindow(event.channel, event, 'Join')

def onJoin(event):
    if 'default' in event.actions:
        event.window.write("* Joins: %s" % event.source)
        event.actions.remove('default')
        
        
        for i in xrange(ui.ui.tabs.get_n_pages()):
            print ui.ui.tabs.get_nth_page(i).title
