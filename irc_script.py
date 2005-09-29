import copy

import events
import conf
import ui
import irc

COMMAND_PREFIX = conf.get("command_prefix") or "/"

def defRaw(e):
    if not e.done:
        if not e.network.got_nick:
            if e.msg[1] in ('431','432','433','436','437'):
                failednick = e.msg[3]
                nicks = list(e.network.nicks)
                
                if failednick in nicks[:-1]:
                    index = nicks.index(failednick)+1
                    e.network.raw('NICK %s' % nicks[index])
                # else get the user to supply a nick or make one up?
        
            elif e.msg[1] == '001':
                if e.network.me != e.msg[2]:
                    e_data = events.data()
                    e_data.network = e.network
                    e_data.window = e.window
                    e_data.source = e.network.me
                    e_data.newnick = e.msg[2]
                    events.trigger('Nick', e_data)
                    e.network.me = e.msg[2]
                    e.network.got_nick = True
                
        if e.msg[1] == "PING":
            e.network.raw("PONG :%s" % e.msg[-1])
            e.done = True
        
        elif e.msg[1] in ("JOIN", "PART", "MODE"):
            e.channel = e.target
            e.text = ' '.join(e.msg[3:])
            events.trigger(e.msg[1].capitalize(), e)
            e.done = True
            
        elif e.msg[1] == "QUIT":
            events.trigger('Quit', e)
            e.done = True
            
        elif e.msg[1] == "KICK":
            e.channel = e.msg[2]
            e.target = e.msg[3]
            events.trigger('Kick', e)
            e.done = True
            
        elif e.msg[1] == "NICK":
            e.newnick = e.msg[2]
            events.trigger('Nick', e)
            if e.network.me == e.source:
                e.network.me = e.newnick

            e.done = True
            
        elif e.msg[1] == "PRIVMSG":
            events.trigger('Text', e)
            e.done = True
        
        elif e.msg[1] == "NOTICE":
            events.trigger('Notice', e)
            e.done = True
        
        elif e.msg[1] == "TOPIC":
            events.trigger('Topic', e)
            e.done = True
        
        elif e.msg[1] in ("376", "422"): #RPL_ENDOFMOTD
            if e.network.status == irc.INITIALIZING:
                e.network.status = irc.CONNECTED
                e_data = copy.copy(e)
                events.trigger('Connect', e_data)
            e.done = True
    
        elif e.msg[1] == "005": #RPL_ISUPPORT
            for arg in e.msg[3:]:
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
                    e.network.isupport[name] = value
                    
                    if name == 'PREFIX':
                        new_prefixes = {}
                        modes, prefixes = value[1:].split(')')
                        for mode, prefix in zip(modes, prefixes):
                            new_prefixes[mode] = prefix
                            new_prefixes[prefix] = mode
                        e.network.prefixes = new_prefixes

def setupSocketConnect(e):
    e.network.got_nick = False
    e.network.isupport = {
        'NETWORK': e.network.server, 
        'PREFIX': '(ohv)@%+',
        'CHANMODES': 'b,k,l,imnpstr',
    }
    e.network.prefixes = {'o':'@', 'h':'%', 'v':'+', '@':'o', '%':'h', '+':'v'}

def defSocketConnect(e):
    if not e.done:
        #this needs to be tested--anyone have a server that uses PASS?
        if e.network.password:
            e.network.raw("PASS :%s" % e.network.password)
        e.network.raw("NICK %s" % e.network.nicks[0])
        e.network.raw("USER %s %s %s :%s" %
              ("urk", "8", "*", e.network.fullname))
              #per rfc2812 these are username, user mode flags, unused, realname
        
        #e.network.me = None
        e.done = True

def defInput(e):
    if not e.done:
        if e.text.startswith(COMMAND_PREFIX):
            command = e.text[len(COMMAND_PREFIX):]
        else:
            command = 'say - '+e.text

        events.run_command(command, e.window, e.network)
        
        e.done = True

def onCommandSay(e):
    if e.window.role in (ui.ChannelWindow, ui.QueryWindow):
        e.network.msg(e.window.id, ' '.join(e.args))
    else:
        raise events.CommandError("There's no one here to speak to.")

def onCommandMsg(e):
    e.network.msg(e.args[0], ' '.join(e.args[1:]))

def onCommandNotice(e):
    e.network.notice(e.args[0], ' '.join(e.args[1:]))

def onCommandQuery(e):
    ui.windows.new(ui.QueryWindow, e.network, e.args[0]).activate()

# make /nick work offline
def onCommandNick(e):
    if not e.network.status:
        e_data = events.data()
        e_data.network = e.network
        e_data.window = ui.get_default_window(e.network)
        e_data.source = e.network.me
        e_data.newnick = e.args[0]
        events.trigger('Nick', e_data)
        e.network.nicks[0] = e.args[0]
        e.network.me = e.args[0]
        
        for w in ui.get_window_for(network=e.network):
            w.nick_label.update()
    else:
        e.network.raw('NICK :%s' % e.args[0])

# make /quit always disconnect us
def onCommandQuit(e):
    if e.network.status:
        e.network.quit(' '.join(e.args))
    else:
        raise events.CommandError("We're not connected to a network.")

def onCommandRaw(e):
    if e.network.status >= irc.INITIALIZING:
        e.network.raw(' '.join(e.args))
    else:
        raise events.CommandError("We're not connected to a network.")

onCommandQuote = onCommandRaw

def onCommandJoin(e):
    if e.args:
        if e.network.status >= irc.INITIALIZING:
            e.network.join(e.args[0])
        else:
            raise events.CommandError("We're not connected.")
    else:
        raise events.CommandError("You must supply a channel.")

def onCommandServer(e):
    network_info = {}

    if len(e.args):
        server = e.args[0]
        if ':' in server:
            server, port = server.rsplit(':', 1)
            network_info["port"] = int(port)
            
        network_info["server"] = server

    if len(e.args) > 1:
        port = e.args[1]
        
        network_info["port"] = int(port)
    
    if 'server' in network_info:
        get_network_info(network_info["server"], network_info)

    new_window = ("n" in e.switches or "m" in e.switches)
    if new_window or not e.network:    
        e.network = irc.Network(**network_info)
        ui.windows.new(ui.StatusWindow, e.network, "status").activate()
        
    if "server" in network_info:
        e.network.server = network_info["server"]
        if not e.network.status:
            window = ui.get_default_window(e.network)
            if window:
                window.title.update()
    if "port" in network_info:
        e.network.port = network_info["port"]

    if not ("n" in e.switches or "o" in e.switches):
        if e.network.status:
            e.network.quit()
        e.network.connect()
        ui.get_default_window(e.network).write(
            "* Connecting to %s on port %s" % (e.network.server, e.network.port))

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

def defCommand(e):
    if not e.done and e.name in trailing:
        if e.network.status >= irc.INITIALIZING:
            if len(e.args) > trailing[e.name]:
                e.network.raw(
                    e.name+' '+
                    ' '.join(e.args[0:trailing[e.name]])+
                    ' :'+' '.join(e.args[trailing[e.name]:]))
            else:
                e.network.raw(e.name+' '+' '.join(e.args))
            e.done = True

def postCommand(e):
    if not e.done and e.network.status >= irc.INITIALIZING:
        e.network.raw(e.text)
        e.done = True
        
def get_network_info(network, network_info):
    conf_info = conf.get("networks/%s/" % network)

    if conf_info:
        network_info["server"] = conf_info["server"] or network
        
        for info in conf_info:
            if info not in network_info:
                network_info[info] = conf_info[info]

def onStart(e):
    on_start_networks = conf.get("start_networks") or []

    for network in on_start_networks:
        network_info = {"server": network}
        get_network_info(network, network_info)
            
        nw = irc.Network(**network_info)
        
        ui.windows.new(ui.StatusWindow, nw, "status").activate()

        nw.connect()

def onConnect(e):
    if 'NETWORK' in e.network.isupport:
        perform = conf.get('perform/'+str(e.network.isupport['NETWORK'])) or []
        for command in perform:
            events.run_command(command, e.window, e.network)
