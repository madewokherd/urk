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
            command = 'say '+event.text

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
    target = event.network.entity(event.args[0])
    if target.window:
        #FIXME: select the window
        pass
    else:
        window = ui.IrcWindow(str(target))
           # str so if we say /query byte and we see Byte, we query Byte
        window.type = 'query'
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
    port = False
    
    server = None
    port = None

    if 'n' in event.switches:
        new_window, connect = True, False

    if 'm' in event.switches:
        new_window = True

    if 'o' in event.switches:
        connect = False

    if event.args:
        server = event.args.pop(0)
        if ':' in server:
            split = server.split(':')
            server = split[0]
            port = int(split[1])
    if event.args:
        port = int(event.args.pop(0))

    if new_window or not event.network:
        event.network = irc.Network("irc.mozilla.org")
        urk.connect(event.network)

    if server:
        event.network.server = server
    if port:
        event.network.port = port
    if connect:
        event.network.connect()

    event.done = True

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
      and event.network.initializing:
        event.network.raw(event.text)
        event.done = True

def onStart(event):
    on_start_networks = conf.get("start_networks") or []

    for network in on_start_networks:
        network_info = conf.get("networks/%s" % network)
        
        if network_info:
            servers = conf.get("networks/%s/%s" % (network, "servers")) or [network]
            port = conf.get("networks/%s/%s" % (network, "port")) or 6667
            nicks = conf.get("networks/%s/%s" % (network, "nicks")) or []
            fullname = conf.get("networks/%s/%s" % (network, "fullname")) or ""

        else:
            servers = [network]
            port = 6667
            nicks = []
            fullname = ""
    
        x = irc.Network(servers[0], port=6667, nicks=nicks, fullname=fullname)
    
        urk.connect(x)
        x.connect()

# FIXME: crush, kill, destroy
def onConnectArlottOrg(event):
    import irc, conf

    x = irc.Network("irc.gimp.org", port=6667, nicks=[], fullname="")
    
    urk.connect(x)
    x.connect()

def defSocketConnect(event):
    if not event.done:
        import conf
        
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
        event.window = ui.make_window(event.network, 'channel', event.target, nicklist=True)
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
        for n, t, i in ui.window_list:
            ui.window_list[n, t, i].nick_label.set_nick(event.newnick)
