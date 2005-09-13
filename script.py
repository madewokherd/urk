import traceback

import events
import irc
import conf
import ui
import webbrowser

import chaninfo

COMMAND_PREFIX = conf.get("command_prefix") or "/"

def onRightClick(event):
    def print_blah():
        print "blah"
        
    event.menu.append(("Print Blah", print_blah))
    
onListRightClick = onWindowMenu = onRightClick

def onClick(event):
    # click on a #channel
    if event.target.startswith("#"):
        if event.target not in event.window.network.channels:
            event.window.network.join(event.target)
        
    # nick on this channel
    target_l = event.target.lstrip('@+%.(<')
    target_fr = event.target_fr + len(event.target) - len(target_l)
    
    target_r = event.target.rstrip(')>:,')
    target_to = event.target_to - len(event.target) + len(target_r)
    
    target = event.text[target_fr:target_to]
    
    #if type(event.window) == ui.ChannelWindow and \
    #        target in event.window.network.channels[event.window.id].nicks:
    #    pass
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    if (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        if target.startswith("www"):
            target = "http://"+target
        ui.open_file(target)

def onHover(event):
    # click on a #channel
    if event.target.startswith("#"):
        event.tolink.add((event.target_fr, event.target_to))
        return
        
    # nick on this channel
    target_l = event.target.lstrip('@+%.(<')
    target_fr = event.target_fr + len(event.target) - len(target_l)
    
    target_r = event.target.rstrip(')>:,')
    target_to = event.target_to - len(event.target) + len(target_r)
    
    target = event.text[target_fr:target_to]
    
    if type(event.window) == ui.ChannelWindow and \
            target in event.window.network.channels[event.window.id].nicks:
        event.tolink.add((target_fr, target_to))        
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        event.tolink.add((target_fr, target_to))

def defInput(event):
    if not event.done:
        if event.text.startswith(COMMAND_PREFIX):
            command = event.text[len(COMMAND_PREFIX):]
        else:
            command = 'say - '+event.text

        events.run_command(command, event.window, event.network)
        
        event.done = True

def handle_say(event):
    if type(event.window) in (ui.ChannelWindow, ui.QueryWindow):
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

def handle_edit(event):
    try:
        args = events.find_script(event.args[0])
    except ImportError:
        event.error_text = "Couldn't find script: %s" % event.args[0]
        return
    if args[1]:
        args[1].close()
        ui.open_file(args[2])
        event.done = True
    else:
        event.error_text = "Couldn't find script: %s" % event.args[0]

def handle_query(event):
    if ui.window_list[event.network, ui.QueryWindow, event.args[0]]:
        ui.window_list[event.network, ui.QueryWindow, event.args[0]].activate()
    else:
        ui.QueryWindow(
            event.network,
            ui.QueryWindow, 
            event.args[0]
            ).activate()

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
        
        for w in ui.get_window_for(network=event.network):
            w.nick_label.update()

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
            server, port = server.rsplit(':', 1)
            network_info["port"] = int(port)
            
        network_info["server"] = server

    if len(event.args) > 1:
        port = event.args[1]
        
        network_info["port"] = int(port)

    get_network_info(network_info["server"], network_info)

    new_window = ("n" in event.switches or "m" in event.switches)
    if new_window or not event.network:    
        event.network = irc.Network(**network_info)
        ui.StatusWindow(
            event.network,
            ui.StatusWindow,
            "Status Window",
            "[%s]" % event.network.server
            ).activate()
        
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
    'edit': handle_edit,
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
    conf_info = conf.get("networks/%s/" % network)

    if conf_info:
        network_info["server"] = conf_info["server"] or network
        
        for info in conf_info:
            if info not in network_info:
                network_info[info] = conf_info[info]

def onStart(event):
    on_start_networks = conf.get("start_networks") or []

    for network in on_start_networks:
        network_info = {"server": network}
        get_network_info(network, network_info)
            
        nw = irc.Network(**network_info)
        
        ui.StatusWindow(
            nw,
            ui.StatusWindow,
            "Status Window",
            "[%s]" % nw.server
            ).activate()

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
        
        #event.network.me = None
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
        if ui.window_list[event.network, ui.QueryWindow, event.source]:
            event.window = ui.window_list[event.network, ui.QueryWindow, event.source]
        else:
            event.window = ui.QueryWindow(event.network, ui.QueryWindow, event.source)
    else:
        event.window = \
            ui.window_list[event.network, ui.ChannelWindow, event.target] or \
            ui.window_list[event.network, ui.QueryWindow, event.target] or \
            event.window

preAction = preText

def preJoin(event):
    if event.source == event.network.me:
        ui.ChannelWindow(event.network, ui.ChannelWindow, event.target).activate()
        
    event.window = ui.window_list[event.network, ui.ChannelWindow, event.target] or event.window

def setupPart(event):
    event.window = ui.window_list[event.network, ui.ChannelWindow, event.target] or event.window

def postPart(event):
    if event.source == event.network.me:
        window = ui.window_list[event.network, ui.ChannelWindow, event.target]
        if window:
            window.close()

setupTopic = setupPart

def setupKick(event):
    event.window = ui.window_list[event.network, ui.ChannelWindow, event.channel] or event.window

def setupMode(event):
    if event.target != event.network.me:
        event.window = ui.window_list[event.network, ui.ChannelWindow, event.target] or event.window

def onClose(window):
    if type(window) == ui.ChannelWindow and window.id in window.network.channels:
        window.network.part(window.id)
    elif type(window) == ui.StatusWindow:
        if window.network.status:
            window.network.quit()
        
        for w in ui.get_window_for(network=window.network):
            if w is not window:
                w.close()   
                
def onNick(event):
    if event.source == event.network.me:
        for w in ui.get_window_for(network=event.network):
            w.nick_label.update(event.newnick)     
