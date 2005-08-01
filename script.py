import traceback
import getopt
import copy

import events
import irc
import conf
import __main__ as urk
import ui

COMMAND_PREFIX = conf.get("command_prefix") or "/"

def run_command(text, window, network):
    if text.startswith(COMMAND_PREFIX):
        text = text[len(COMMAND_PREFIX):]
    split = text.split()
    e_data = events.data()
    e_data.name = split[0]
    e_data.args = split[1:]
    e_data.text = text
    e_data.type = 'command'
    e_data.window = window
    e_data.network = network
    e_data.error_text = 'No such command exists'
    events.trigger('Command', e_data)
    if not e_data.done:
        event.window.write("* /%s: %s" % (e_data.name, e_data.error_text))

def defInput(event):
    if not event.done:
        if event.text.startswith(COMMAND_PREFIX):
            command = event.text[len(COMMAND_PREFIX):]
        else:
            command = 'say '+event.text
        run_command(command, event.window, event.network)

def handle_say(event):
    if event.window.type in ('channel', 'user'):
        event.network.msg(event.window.target, ' '.join(event.args))
        event.done = True
    else:
        event.error_text = "There's no one here to speak to."

def handle_msg(event):
    event.network.msg(event.args[0], ' '.join(event.args[1:]))
    event.done = True

def handle_me(event):
    if event.window.type in ('channel', 'user'):
        event.network.emote(event.window.target, ' '.join(event.args))
        event.done = True
    else:
        event.error_text = "There's no one here to speak to."

def handle_echo(event):
    event.window.write(' '.join(event.args))
    event.done = True

def handle_query(event):
    target = event.network.entity(event.args[0])
    if target.window:
        #FIXME: select the window
        pass
    else:
        window = ui.IrcWindow(str(target))
           # str so if we say /query byte and we see Byte, we query Byte
        window.type = 'user'
        window.target = target
        target.window = window
        ui.new_tab(target.window, event.network)
    event.done = True

def handle_raw(event):
    if event.network.initializing:
        event.network.raw(' '.join(event.args))
        event.done = True
    else:
        event.error_text = "We're not connected to a network."

def handle_join(event):
    if event.args:
        if event.network.initializing:
            event.network.join(event.args[0])
            event.done = True
        else:
            event.error_text = "We're not connected."
    else:
        event.error_text = "You must supply a channel."

def handle_pyeval(event):
    try:
        event.window.write(repr(eval(' '.join(event.args), globals(), event.__dict__)))
    except:
        for line in traceback.format_exc().split('\n'):
            event.window.write(line)
    event.done = True

def handle_pyexec(event):
    try:
        exec ' '.join(event.args) in globals(), event.__dict__
    except:
        for line in traceback.format_exc().split('\n'):
            event.window.write(line)
    event.done = True

def handle_reload(event):
    name = event.args[0]
    events.refresh(name)
    event.done = True

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
    event.done = True

command_handlers = {
    'say': handle_say,
    'msg': handle_msg,
    'me': handle_me,
    'echo': handle_echo,
    'query': handle_query,
    'raw': handle_raw,
    'quote': handle_raw,
    'join': handle_join,
    'pyeval': handle_pyeval,
    'pyexec': handle_pyexec,
    'reload': handle_reload,
    'server': handle_server,
}

def defCommand(event):
    if not event.done and event.name in command_handlers:
        command_handlers[event.name](event)

def postCommand(event):
    if not event.done and event.error_text == 'No such command exists' \
      and event.network.initializing:
        event.network.raw(event.text)
        event.done = True

def get_server(network):
    #FIXME: We should check if network is in a list of networks before falling
    # back on this.
    return network

def onStart(event):
    on_start_networks = conf.get("start_networks") or []

    for network in on_start_networks:
        server = get_server(network)
    
        x = irc.Network("Urk user", conf.get("nick"), server)
    
        ui.enqueue(urk.connect, x)
    
        x.connect()
    
        # FIXME, given a network, might we want to look up servers?, possibly 
        #        this should happen on instantiation of the Network() otherwise
        #        i guess it should be done whenever we need to connect to a
        #        network, ie. here and some other places
        
# FIXME: crush, kill, destroy
def onConnectArlottOrg(event):
    import irc, conf
    
    server = get_server("irc.mozilla.org")

    x = irc.Network("Urk user", conf.get("nick"), server)
    
    urk.connect(x)
    
    x.connect()

def defRaw(event):
    if not event.done:
        if not event.network.me:
            if event.msg[1] == '001':
                event.network.me = event.network.entity(event.msg[2])
                event.network.initializing = True
            elif event.msg[1] in ('431','432','433','436','437'):
                failednick = event.msg[3]
                nicks = [event.network.nick] + list(event.network.anicks)
                if failednick in nicks[:-1]:
                    index = nicks.index(failednick)+1
                    event.network.raw('NICK %s' % nicks[index])
                # else get the user to supply a nick or make one up?
        
        if event.msg[1] == "PING":
            event.network.raw("PONG :%s" % event.msg[-1])
            event.done = True
            event.quiet = True
        
        elif event.msg[1] == "JOIN":
            event.channel = event.target
            event.type = "join"
            events.trigger('Join', event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "PRIVMSG":
            if event.text[0] == '\x01' and event.text[-1] == '\x01':
                e_data = copy.copy(event)
                e_data.type = 'ctcp'
                e_data.text = event.text[1:-1]
                tokens = e_data.text.split(' ')
                e_data.name = tokens[0]
                e_data.args = tokens[1:]
                events.trigger('Ctcp', e_data)
            else:
                event.type = "text"
                events.trigger('Text', event)
            event.done = True
            event.quiet = True
        
        elif event.msg[1] == "005": #RPL_ISUPPORT
            for arg in event.msg[3:]:
                if ' ' not in arg: #ignore "are supported by this server"
                    if '=' in arg:
                        split = arg.split('=')
                        name = split[0]
                        value = '='.join(split[1:])
                        if value.isdigit():
                            value = int(value)
                    else:
                        name = arg
                        value = ''
                    #in theory, we're supposed to replace \xHH with the
                    # corresponding ascii character, but I don't think anyone
                    # relies on this
                    event.network.isupport[name] = value    
            event.done = True
        
        elif event.msg[1] == "376": #RPL_ENDOFMOTD
            if not event.network.connected:
                event.network.connected = True
                e_data = copy.copy(event)
                e_data.type = 'connect'
                events.trigger('Connect', e_data)
            event.done = True

def setupSocketConnect(event):
    event.network.isupport = {'NETWORK': event.network.server, 'PREFIX': '(ohv)@%+'}

def defSocketConnect(event):
    if not event.done:
        import conf
        
        #this needs to be tested--anyone have a server that uses PASS?
        if event.network.password:
            event.network.raw("PASS :%s" % event.network.password)
        event.network.raw("NICK %s" % event.network.nick)
        event.network.raw("USER %s %s %s :%s" %
              ("urk", "8", "*", event.network.fullname))
              #per rfc2812 these are username, user mode flags, unused, realname
        
        event.network.me = None
        event.done = True

def defConnect(event):
    if not event.done:
        if 'NETWORK' in event.network.isupport:
            perform = conf.get('perform/'+str(event.network.isupport['NETWORK'])) or []
            for command in perform:
                run_command(command, event.window, event.network)
            event.done = True

def setupDisconnect(event):
    if not hasattr(event, 'window'):
        event.window = urk.get_window[event.network]
        
    event.type = "disconnect"

def defNewWindow(event):
    if not event.done:
        if event.target.type == 'channel':
            window = ui.IrcChannelWindow(str(event.target))
        else:
            window = ui.IrcWindow(str(event.target))
        event.target.window = window
        event.window = window
        window.type = event.target.type
        window.target = event.target
        ui.new_tab(window, event.target.network)
        event.done = True

def setupJoin(event):
    event.window = ui.get_window(event.target, event, 'Join')

def defJoin(event):
    if not event.done and event.source == event.network.me:
        ui.activate(event.window)

def setupText(event):
    if event.target == event.network.me:
        event.window = ui.get_window(event.source, event, 'Text')
    else:
        event.window = ui.get_window(event.target, event, 'Text')

def defCtcp(event):
    if not event.done:
        if event.name == 'ACTION':
            e_data = copy.copy(event)
            e_data.type = 'action'
            e_data.text = ' '.join(event.args)
            events.trigger('Action', e_data)
        event.done = True

def setupAction(event):
    if event.target == event.network.me:
        event.window = ui.get_window(event.source, event, 'Text')
    else:
        event.window = ui.get_window(event.target, event, 'Text')
