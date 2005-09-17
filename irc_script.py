import copy

import events
import conf
import ui
import irc

COMMAND_PREFIX = conf.get("command_prefix") or "/"

def defRaw(event):
    if not event.done:
        if not event.network.got_nick:
            if event.msg[1] in ('431','432','433','436','437'):
                failednick = event.msg[3]
                nicks = list(event.network.nicks)
                
                if failednick in nicks[:-1]:
                    index = nicks.index(failednick)+1
                    event.network.raw('NICK %s' % nicks[index])
                # else get the user to supply a nick or make one up?
        
            elif event.msg[1] == '001':
                if event.network.me != event.msg[2]:
                    e_data = events.data()
                    e_data.network = event.network
                    e_data.window = event.window
                    e_data.source = event.network.me
                    e_data.newnick = event.msg[2]
                    events.trigger('Nick', e_data)
                    event.network.me = event.msg[2]
                    event.network.got_nick = True
                
        if event.msg[1] == "PING":
            event.network.raw("PONG :%s" % event.msg[-1])
            event.done = True
        
        elif event.msg[1] in ("JOIN", "PART", "MODE"):
            event.channel = event.target
            event.text = ' '.join(event.msg[3:])
            events.trigger(event.msg[1].capitalize(), event)
            event.done = True
            
        elif event.msg[1] == "QUIT":
            events.trigger('Quit', event)
            event.done = True
            
        elif event.msg[1] == "KICK":
            event.channel = event.msg[2]
            event.target = event.msg[3]
            events.trigger('Kick', event)
            event.done = True
            
        elif event.msg[1] == "NICK":
            event.newnick = event.msg[2]
            events.trigger('Nick', event)
            if event.network.me == event.source:
                event.network.me = event.newnick

            event.done = True
            
        elif event.msg[1] == "PRIVMSG":
            events.trigger('Text', event)
            event.done = True
        
        elif event.msg[1] == "NOTICE":
            events.trigger('Notice', event)
            event.done = True
        
        elif event.msg[1] == "TOPIC":
            events.trigger('Topic', event)
            event.done = True
        
        elif event.msg[1] == "376": #RPL_ENDOFMOTD
            if event.network.status == irc.INITIALIZING:
                event.network.status = irc.CONNECTED
                e_data = copy.copy(event)
                events.trigger('Connect', e_data)
            event.done = True
    
        elif event.msg[1] == "005": #RPL_ISUPPORT
            for arg in event.msg[3:]:
                if ' ' not in arg: #ignore "are supported by this server"
                    if '=' in arg:
                        name, value = arg.split('=', 1)
                        if value.isdigit():
                            value = int(value)
                    else:
                        name, value = arg, ''

                    #in theory, we're supposed to replace \xHH with the
                    # corresponding ascii character, but I don't think anyone
                    # really does this
                    event.network.isupport[name] = value
                    
                    if name == 'PREFIX':
                        new_prefixes = {}
                        modes, prefixes = value[1:].split(')')
                        for mode, prefix in zip(modes, prefixes):
                            new_prefixes[mode] = prefix
                            new_prefixes[prefix] = mode
                        event.network.prefixes = new_prefixes

def setupSocketConnect(event):
    event.network.got_nick = False
    event.network.isupport = {
        'NETWORK': event.network.server, 
        'PREFIX': '(ohv)@%+',
        'CHANMODES': 'b,k,l,imnpstr',
    }
    event.network.prefixes = {'o':'@', 'h':'%', 'v':'+', '@':'o', '%':'h', '+':'v'}

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

def handle_query(event):
    ui.windows.new(ui.QueryWindow, event.network, event.args[0]).activate()
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

handle_quote = handle_raw

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
    
    if 'server' in network_info:
        get_network_info(network_info["server"], network_info)

    new_window = ("n" in event.switches or "m" in event.switches)
    if new_window or not event.network:    
        event.network = irc.Network(**network_info)
        ui.windows.new(ui.StatusWindow, event.network, "status").activate()
        
    if "server" in network_info:
        event.network.server = network_info["server"]
        if not event.network.status:
            window = ui.get_status_window(event.network)
            if window:
                window.title.update()
    if "port" in network_info:
        event.network.port = network_info["port"]

    if not ("n" in event.switches or "o" in event.switches):
        if event.network.status:
            event.network.quit()
        event.network.connect()
        ui.get_status_window(event.network).write(
            "* Connecting to %s on port %s" % (event.network.server, event.network.port))
    
    event.done = True

#commands that we need to add a : to but otherwise can send unchanged
#the dictionary contains the number of arguments we take without adding the :
trailing = {
    'away':0,
    'cnotice':2,
    'cprivmsg':2,
    'kick':2,
    'kill':1,
    'part':1,
    'squery':1,
    'squit':1,
    'topic':1,
    'wallops':0,
    }

def defCommand(event):
    if not event.done:
        if 'handle_%s' % event.name in globals():
            globals()['handle_%s' % event.name](event)
        elif event.name in trailing:
            if event.network.status >= irc.INITIALIZING:
                if len(event.args) > trailing[event.name]:
                    event.network.raw(
                        event.name+' '+
                        ' '.join(event.args[0:trailing[event.name]])+
                        ' :'+' '.join(event.args[trailing[event.name]:]))
                else:
                    event.network.raw(event.name+' '+' '.join(event.args))
                event.done = True
            else:
                event.error_text = "We're not connected to a network."

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
        
        ui.windows.new(ui.StatusWindow, nw, "status").activate()

        nw.connect()

def onConnect(event):
    if 'NETWORK' in event.network.isupport:
        perform = conf.get('perform/'+str(event.network.isupport['NETWORK'])) or []
        for command in perform:
            events.run_command(command, event.window, event.network)
