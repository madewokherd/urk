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
        events.trigger('Command', events.data(
           name=split[0],
           args=split[1:],
           text=event.command,
           window=event.window,
           network=event.network,
           ))
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
        

command_handlers = {
    'echo': handle_echo,
    'query': handle_query,
}

def setupCommand(event):
    if not hasattr(event, 'actions'):
        event.actions = set(['default'])

def onCommand(event):
    if 'default' in event.actions and event.name in command_handlers:
        command_handlers[event.name](event)
        event.actions.remove('default')

def postCommand(event):
    if 'default' in event.actions:
        event.window.write("Unknown command: "+event.name)
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
    import irc

    x = irc.Network("irc.arlott.org", "MrUrk", "blackhole.arlott.org")
    
    urk.connect(x)

def onRaw(event):
    if event.msg[1] == "PING":
        event.network.raw("PONG :%s" % event.msg[-1])
        
    event.window.write(event.rawmsg)
        
def onSocketConnect(event):
    event.network.raw("NICK %s" % "MrUrk")
    event.network.raw("USER %s %s %s :%s" % ("a", "b", "c", "MrUrk"))
        
def onDisconnect(event):
    print "disconnect"
