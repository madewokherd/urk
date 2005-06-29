import events
import __main__ as urk
import ui

def setupInput(event):
    command_char = "/"

    if not hasattr(event, 'todo'):
        event.todo = set()
        
    if event.text[0] == command_char:
        event.todo.add('command')
        event.command = event.text[1:]
    else:
        event.todo.add('default')

def onInput(event):
    if 'command' in event.todo:
        split = event.command.split()
        e_data = events.data()
        e_data.name = split[0]
        e_data.args = split[1:]
        e_data.text = event.command
        e_data.window = event.window
        e_data.network = event.network
        events.trigger('Command', e_data)
        if 'default' in e_data.todo:
            event.window.write('Unknown command: '+e_data.name)
        event.todo.remove('command')
    if 'default' in event.todo and event.window.type in ('channel', 'user'):
        event.network.msg(event.window.target, event.text)
        event.todo.remove('default')

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
        window.type = user
        window.target = target
        target.window = window
        ui.new_tab(target.window, event.network)

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
        
    if event.args:
        if event.network.connected:
            # FIXME: We might want to activate tabs for channels we /joined
            event.network.join(event.args[0])
        else:
            event.window.write("* /join: We're not connected.")
    else:
        event.window.write("* /join: You must supply a channel.")

def handle_pyeval(event):
    event.window.write(repr(eval(' '.join(event.args), globals(), event.__dict__)))

def handle_pyexec(event):
    exec ' '.join(event.args) in globals(), event.__dict__

command_handlers = {
    'echo': handle_echo,
    'query': handle_query,
    'raw': handle_raw,
    'quote': handle_raw,
    'join': handle_join,
    'pyeval': handle_pyeval,
    'pyexec': handle_pyexec,
}

def setupCommand(event):
    if not hasattr(event, 'todo'):
        event.todo = set(['default'])

def onCommand(event):
    if 'default' in event.todo and event.name in command_handlers:
        command_handlers[event.name](event)
        event.todo.remove('default')

def postCommand(event):
    if 'default' in event.todo and event.network.connected:
        event.network.raw(event.text)
        event.todo.remove('default')

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

    x = irc.Network("irc.gamesurge.net", conf.get("nick"), "irc.gamesurge.net")
    
    urk.connect(x)

def onRaw(event):
    if event.msg[1] == "PING":
        event.network.raw("PONG :%s" % event.msg[-1])
    
    e_data = events.data()
    e_data.msg = event.msg
    e_data.rawmsg = event.rawmsg
    e_data.source = event.source
    
    if not event.network.me and event.msg[1] == '001':
        event.network.me = event.network.user(event.msg[2])
    
    if event.msg[1] == "JOIN":
        e_data.channel = event.network.channel(event.msg[2])
        e_data.target = e_data.channel
        events.trigger('Join', e_data)
    elif event.msg[1] == "PRIVMSG":
        e_data.target = event.network.entity(event.msg[2])
        e_data.text = event.msg[-1]
        events.trigger('Text', e_data)
    
    event.window.write(event.rawmsg)

def onSocketConnect(event):
    import conf

    event.network.raw("NICK %s" % conf.get("nick"))
    event.network.raw("USER %s %s %s :%s" % ("a", "b", "c", "MrUrk"))
    
    event.network.me = None

def setupDisconnect(event):
    if not hasattr(event, 'window'):
        event.window = urk.get_window[event.network]
    if not hasattr(event, 'todo'):
        event.todo = set(['default'])

def onDisconnect(event):
    if 'default' in event.todo:
        if event.error:
            print event.error
        event.window.write('* Disconnected')
        event.todo.remove('default')

def setupNewWindow(event):
    if not hasattr(event, 'todo'):
        event.todo = set(['default'])
    else:
        event.todo.add('default')
    #FIXME: This should be 'virtual' if we don't want to make a new window
    # and onNewWindow should handle it.

def onNewWindow(event):
    if 'default' in event.todo:
        if event.target.type == 'channel':
            window = ui.IrcChannelWindow(str(event.target))
        else:
            window = ui.IrcWindow(str(event.target))
        event.target.window = window
        event.window = window
        window.type = event.target.type
        window.target = event.target
        ui.new_tab(window, event.target.network)
        event.todo.remove('default')

def setupJoin(event):
    if not hasattr(event, 'todo'):
        event.todo = set(['default'])
    else:
        event.todo.add('default')

    event.window = ui.getWindow(event.target, event, 'Join')

def onJoin(event):
    if 'default' in event.todo:
        event.window.write("* Joins: %s" % event.source)
        event.todo.remove('default')
            
        ui.activate(window)

def setupText(event):
    if not hasattr(event, 'todo'):
        event.todo = set(['default'])
    else:
        event.todo.add('default')

    event.window = ui.getWindow(event.target, event, 'Text')

def onText(event):
    if 'default' in event.todo:
        event.window.write("<%s> %s" % (event.source, event.text))
        event.todo.remove('default')
