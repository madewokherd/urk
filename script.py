import events

def onStart(event):
    print "Omg, we've started"
    
def preJoin(event):
    print "pre", "join"
    
def dothebartmanJoin(event):
    print "bartman", "join"
    
def dothebartmanPart(event):
    print "bartmano", "part"

def setupInput(event):
    if not hasattr(event, 'actions'):
        event.actions = set()
        
    if event.text[0] == '/':
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
           ))
        event.actions.remove('command')

#should this be something like onCommandEcho?
#if so, how?
def handle_echo(event):
    event.window.write(' '.join(event.args))

command_handlers = {
    'echo': handle_echo,
}

def onCommand(event):
    if 'default' in event.actions and event.name in command_handlers:
        command_handlers[event.name](event)
        event.actions.remove('default')

def postCommand(event):
    if 'default' in event.actions:
        event.window.write("Unknown command: "+event.name)
        event.actions.remove('default')

def onStart(event):
    # FIXME, find a list of networks to join from somewhere, prolly conf
    #         then join them
    def list_of_networks_to_join_from_somewhere():
        return ["ANet", "BNet", "CNet"]
    
    on_start_networks = list_of_networks_to_join_from_somewhere()
    
    for network in on_start_networks:
        # FIXME, connect to it
        #        how do we do this?
        #        we prolly call something.connect(network)
        #        or else maybe we create a network object and call
        #        network_object.connect()
        
        print "Connecting to %s" % network

def onRaw(event):
    if event.msg[1] == "PONG":
        event.network.raw("PONG :%s" % event.msg[-1])
        
def onDisconnect(event):
    print "disconnect"
