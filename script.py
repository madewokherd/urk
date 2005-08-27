import traceback

import events
import irc
import conf
import ui

COMMAND_PREFIX = conf.get("command_prefix") or "/"

def run_command(text, window, network):
    if not text:
        return

    split = text.split()

    c_data = events.data()
    c_data.text = text
    
    c_data.name = split[0]

    if len(split) > 1 and split[1][0] == "-":
        c_data.switches = set(split[1][1:])
        c_data.args = split[2:]
    else:
        c_data.switches = set()
        c_data.args = split[1:]

    c_data.window = window
    c_data.network = network

    c_data.error_text = 'No such command exists'

    events.trigger('Command', c_data)
    
    if not c_data.done:
        c_data.window.write("* /%s: %s" % (c_data.name, c_data.error_text))

def defInput(event):
    if not event.done:
        if event.text.startswith(COMMAND_PREFIX):
            command = event.text[len(COMMAND_PREFIX):]
        else:
            command = 'say - '+event.text

        run_command(command, event.window, event.network)

def handle_say(event):
    if event.window.type in ('channel', 'query'):
        event.network.msg(event.window.id, ' '.join(event.args))
        event.done = True
    else:
        event.error_text = "There's no one here to speak to."

def handle_msg(event):
    event.network.msg(event.args[0], ' '.join(event.args[1:]))
    event.done = True

def handle_me(event):
    if event.window.type in ('channel', 'query'):
        event.network.emote(event.window.id, ' '.join(event.args))
        event.done = True
    else:
        event.error_text = "There's no one here to speak to."

def handle_notice(event):
    event.network.notice(event.args[0], ' '.join(event.args[1:]))
    event.done = True

def handle_echo(event):
    event.window.write(' '.join(event.args))
    event.done = True

def handle_query(event):
    window = ui.make_window(event.network, 'query', event.args[0])
    ui.activate(window)
    event.done = True

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
        window = ui.make_window(event.network, 'status', "Status Window", "[%s]" % event.network.server)
        ui.activate(window)
        
    if "server" in network_info:
        event.network.server = network_info["server"]
    if "port" in network_info:
        event.network.port = network_info["port"]

    if not ("n" in event.switches or "o" in event.switches):
        if event.network.status:
            event.network.quit()
        event.network.connect()

    event.done = True
    
    print network_info

command_handlers = {
    'say': handle_say,
    'msg': handle_msg,
    'me': handle_me,
    'notice': handle_notice,
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
      and event.network.status >= irc.INITIALIZING:
        event.network.raw(event.text)
        event.done = True
        
def get_network_info(network, network_info):
    #FIXME: if conf.get("networks/%s" % network):
    
    for info in ("server", "port", "nicks", "fullname"):
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
        
        window = ui.make_window(nw, 'status', "Status Window", "[%s]" % nw.server)
        ui.activate(window)

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

def defConnect(event):
    if 'NETWORK' in event.network.isupport:
        perform = conf.get('perform/'+str(event.network.isupport['NETWORK'])) or []
        for command in perform:
            run_command(command, event.window, event.network)
        event.done = True

def setupText(event):
    if event.target == event.network.me:
        event.window = ui.make_window(event.network, 'query', event.source)
    else:
        event.window = \
            ui.window_list[event.network, 'channel', event.target] or \
            ui.window_list[event.network, 'query', event.target] or \
            event.window

setupAction = setupText

def setupJoin(event):
    if event.source == event.network.me:
        event.window = ui.make_window(event.network, 'channel', event.target, is_chan=True)
        ui.activate(event.window)

    event.window = ui.window_list[event.network, 'channel', event.target] or event.window

def setupPart(event):
    event.window = ui.window_list[event.network, 'channel', event.target] or event.window

def postPart(event):
    if event.source == event.network.me:
        window = ui.window_list[event.network, 'channel', event.target]
        if window:
            ui.close_window(window)

setupTopic = setupPart

def setupKick(event):
    event.window = ui.window_list[event.network, 'channel', event.channel] or event.window

def setupMode(event):
    if event.target != event.network.me:
        event.window = ui.window_list[event.network, 'channel', event.target] or event.window

def onClose(window):
    if window.type == 'channel' and window.id in window.network.channels:
        window.network.part(window.id)

def onNick(event):
    if event.network.me == event.source:
        for window in ui.get_window_for(network=event.network):
            window.nick_label.set_nick(event.newnick)
