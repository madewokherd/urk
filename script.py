import traceback
import getopt

import events
import irc
import conf
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
    target = event.network.entity(event.args[0])
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
    if event.args:
        if event.network.connected:
            # FIXME: We might want to activate tabs for channels we /joined
            event.network.join(event.args[0])
        else:
            event.window.write("* /join: We're not connected.")
    else:
        event.window.write("* /join: You must supply a channel.")

def handle_pyeval(event):
    try:
        event.window.write(repr(eval(' '.join(event.args), globals(), event.__dict__)))
    except:
        for line in traceback.format_exc().split('\n'):
            event.window.write(line)

def handle_pyexec(event):
    try:
        exec ' '.join(event.args) in globals(), event.__dict__
    except:
        for line in traceback.format_exc().split('\n'):
            event.window.write(line)

def handle_server(event):
    new_window = False
    connect = True
    port = None
    server = None
    options, args = getopt.gnu_getopt(event.args,"nomp:",['new','noconnect','port='])
    options = dict(options)
    if ('-n' in options):
        new_window, connect = True, False
    if ('-m' in options) or ('--new' in options):
        new_window = True
    if ('-o' in options) or ('--noconnect' in options):
        connect = False
    if ('-p' in options):
        port = options['-p']
    if ('--port' in options):
        port = options['--port']
    if args:
        server = args.pop(0)
        if ':' in server:
            split = server.split(':')
            server = split[0]
            port = int(split[1])
    if args:
        port = int(args.pop(0))
    
    def do_server():
        if new_window or not event.network:
            network = irc.Network("Urk user", conf.get("nick"), "irc.mozilla.org")
            urk.connect(network)
        else:
            network = event.network
        if server:
            network.server = server
        if port:
            network.port = port
        if connect:
            network.connect()
    
    ui.enqueue(do_server)

command_handlers = {
    'echo': handle_echo,
    'query': handle_query,
    'raw': handle_raw,
    'quote': handle_raw,
    'join': handle_join,
    'pyeval': handle_pyeval,
    'pyexec': handle_pyexec,
    'server': handle_server,
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

    x = irc.Network("Urk user", conf.get("nick"), "irc.mozilla.org")
    
    urk.connect(x)
    
    x.connect()

def onRaw(event):
    if event.msg[1] == "PING":
        event.network.raw("PONG :%s" % event.msg[-1])
    
    e_data = events.data()
    e_data.msg = event.msg
    e_data.rawmsg = event.rawmsg
    e_data.source = event.source
    
    if not event.network.me:
        if event.msg[1] == '001':
            event.network.me = event.network.entity(event.msg[2])
            event.network.connected = True
        elif event.msg[1] in ('431','432','433','436','437'):
            failednick = event.msg[3]
            nicks = [event.network.nick] + list(event.network.anicks)
            if failednick in nicks[:-1]:
                index = nicks.index(failednick)+1
                event.network.raw('NICK %s' % nicks[index])
            # else get the user to supply a nick or make one up?
    
    if event.msg[1] == "JOIN":
        e_data.channel = event.network.entity(event.msg[2])
        e_data.target = e_data.channel
        events.trigger('Join', e_data)
    elif event.msg[1] == "PRIVMSG":
        e_data.target = event.network.entity(event.msg[2])
        e_data.text = event.msg[-1]
        events.trigger('Text', e_data)
    
    event.window.write(event.rawmsg)

def onSocketConnect(event):
    import conf
    
    #this needs to be tested--anyone have a server that uses PASS?
    if event.network.password:
        event.network.raw("PASS :%s" % event.network.password)
    event.network.raw("NICK %s" % event.network.nick)
    event.network.raw("USER %s %s %s :%s" %
          ("a", "b", "c", event.network.fullname))
    
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

    event.window = ui.get_window(event.target, event, 'Join')

def onJoin(event):
    if 'default' in event.todo:
        event.window.write("* Joins: %s" % event.source)
        event.todo.remove('default')
            
        ui.activate(event.window)

def setupText(event):
    if not hasattr(event, 'todo'):
        event.todo = set(['default'])
    else:
        event.todo.add('default')

    event.window = ui.get_window(event.target, event, 'Text')

def onText(event):
    if 'default' in event.todo:
        event.window.write("<%s> %s" % (event.source, event.text))
        event.todo.remove('default')
