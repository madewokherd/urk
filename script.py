import traceback

import events
import irc
import conf
import ui

COMMAND_PREFIX = conf.get("command_prefix") or "/"

events.load('irc_basicinfo')

def onHover(event):
    fr = to = 0
    
    for word in event.text.split(" "):
        to += len(word)
        
        if fr <= event.pos < to and word == "marc":
            event.tolink += [(fr, to)]
            break
            
        fr += len(word)
        
        fr += 1
        to += 1

def defInput(event):
    if not event.done:
        if event.text.startswith(COMMAND_PREFIX):
            command = event.text[len(COMMAND_PREFIX):]
        else:
            command = 'say - '+event.text

        events.run_command(command, event.window, event.network)
        
        event.done = True

def handle_say(event):
    if event.window.type in ('channel', 'query'):
        event.network.msg(event.window.id, ' '.join(event.args))
        event.done = True
    else:
        event.error_text = "There's no one here to speak to."

def handle_msg(event):
    event.network.msg(event.args[0], ' '.join(event.args[1:]))
    event.done = True

def handle_notice(event):
    event.network.notice(event.args[0], ' '.join(event.args[1:]))
    event.done = True

def handle_echo(event):
    event.window.write(' '.join(event.args))
    event.done = True

def handle_query(event):
    window = ui.QueryWindow(event.network, 'query', event.args[0])
    window.activate()
    event.done = True

# make /nick work offline
def handle_nick(event):
    if not event.network.status:
        e_data = events.data()
        e_data.network = event.network
        e_data.window = ui.get_status_window(event.network)
        e_data.source = event.network.me
        e_data.newnick = event.args[0]
        events.trigger('Nick', e_data)
        event.network.nicks[0] = event.args[0]
        event.network.me = event.args[0]
        event.done = True

# make /quit always disconnect us
def handle_quit(event):
    if event.network.status:
        event.network.quit(' '.join(event.args))
        event.done = True
    else:
        event.error_text = "We're not connected to a network."

def handle_raw(event):
    if event.network.status >= irc.INITIALIZING:
        event.network.raw(' '.join(event.args))
        event.done = True
    else:
        event.error_text = "We're not connected to a network."

def handle_join(event):
    if event.args:
        if event.network.status >= irc.INITIALIZING:
            event.network.join(event.args[0])
            event.done = True
        else:
            event.error_text = "We're not connected."
    else:
        event.error_text = "You must supply a channel."

def handle_server(event):
    network_info = {}

    if len(event.args):
        server = event.args[0]
        if ':' in server:
            server, port = server.split(':')
            network_info["port"] = int(port)
            
        network_info["server"] = server

    if len(event.args) > 1:
        port = event.args[1]
        
        network_info["port"] = int(port)

    if "server" in network_info:    
        network_info = get_network_info(network_info["server"], network_info)

    new_window = ("n" in event.switches or "m" in event.switches)
    if new_window or not event.network:    
        event.network = irc.Network(**network_info)
        window = ui.ServerWindow(
                    event.network,
                    'status',
                    "Status Window",
                    "[%s]" % event.network.server
                    )
        window.activate()
        
    if "server" in network_info:
        event.network.server = network_info["server"]
        if not event.network.status:
            window = ui.get_status_window(event.network)
            if window:
                window.title = "[%s]" % event.network.server
    if "port" in network_info:
        event.network.port = network_info["port"]

    if not ("n" in event.switches or "o" in event.switches):
        if event.network.status:
            event.network.quit()
        event.network.connect()
        ui.get_status_window(event.network).write(
            "* Connecting to %s on port %s" % (event.network.server, event.network.port))
    
    event.done = True

command_handlers = {
    'say': handle_say,
    'msg': handle_msg,
    'notice': handle_notice,
    'echo': handle_echo,
    'query': handle_query,
    'nick': handle_nick,
    'quit': handle_quit,
    'raw': handle_raw,
    'quote': handle_raw,
    'join': handle_join,
    'server': handle_server,
    }

def defCommand(event):
    if not event.done and event.name in command_handlers:
        command_handlers[event.name](event)

def postCommand(event):
    if not event.done and event.error_text == 'No such command exists' \
      and event.network.status >= irc.INITIALIZING:
        event.network.raw(event.text)
        event.done = True
        
def get_network_info(network, network_info):
    key_info = conf.get("networks/%s/server" % network)
    if key_info:
        network_info["server"] = key_info
    
        for info in ("port", "nicks", "fullname"):
            if info not in network_info:
                key_info = conf.get("networks/%s/%s" % (network, info))
        
                if key_info:
                    network_info[info] = key_info

    return network_info

def onStart(event):
    on_start_networks = conf.get("start_networks") or []

    for network in on_start_networks:
        network_info = get_network_info(network, {}) or {"server": network}
            
        nw = irc.Network(**network_info)
        
        window = ui.ServerWindow(nw, 'status', "Status Window", "[%s]" % nw.server)
        window.activate()

        nw.connect()

def defSocketConnect(event):
    if not event.done:
        #this needs to be tested--anyone have a server that uses PASS?
        if event.network.password:
            event.network.raw("PASS :%s" % event.network.password)
        event.network.raw("NICK %s" % event.network.nicks[0])
        event.network.raw("USER %s %s %s :%s" %
              ("urk", "8", "*", event.network.fullname))
              #per rfc2812 these are username, user mode flags, unused, realname
        
        event.network.me = None
        event.done = True

def onConnect(event):
    if 'NETWORK' in event.network.isupport:
        perform = conf.get('perform/'+str(event.network.isupport['NETWORK'])) or []
        for command in perform:
            events.run_command(command, event.window, event.network)
    window = ui.get_status_window(event.network)
    if window:
        #window.title = event.network.isupport['NETWORK']
        # If we use the network name, it can make it harder to tell which
        # windows are status windows. We need a better solution, but this is
        # disabled for now.
        window.title = event.network.server

def onDisconnect(event):
    window = ui.get_status_window(event.network)
    if window:
        window.title = "[%s]" % event.network.server

def preText(event):
    if event.target == event.network.me:
        event.window = ui.QueryWindow(event.network, 'query', event.source)
    else:
        event.window = \
            ui.window_list[event.network, 'channel', event.target] or \
            ui.window_list[event.network, 'query', event.target] or \
            event.window

preAction = preText

def preJoin(event):
    if event.source == event.network.me:
        event.window = ui.ChannelWindow(event.network, 'channel', event.target)
        event.window.activate()

    event.window = ui.window_list[event.network, 'channel', event.target] or event.window

def setupPart(event):
    event.window = ui.window_list[event.network, 'channel', event.target] or event.window

def postPart(event):
    if event.source == event.network.me:
        window = ui.window_list[event.network, 'channel', event.target]
        if window:
            window.close()

setupTopic = setupPart

def setupKick(event):
    event.window = ui.window_list[event.network, 'channel', event.channel] or event.window

def setupMode(event):
    if event.target != event.network.me:
        event.window = ui.window_list[event.network, 'channel', event.target] or event.window

def onClose(window):
    if window.type == 'channel' and window.id in window.network.channels:
        window.network.part(window.id)
    elif window.type == 'status':
        if window.network.status:
            window.network.quit()
        
        for w in ui.get_window_for(network=window.network):
            if w is not window:
                w.close()
