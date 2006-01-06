import time

import events
from conf import conf
import ui
import irc
from urllib import unquote

COMMAND_PREFIX = conf.get('command_prefix', '/')

NICK_SUFFIX = r"`_-\|0123456789"

#for getting a list of alternative nicks to try on a network
def _nick_generator(network):
    for nick in network.nicks[1:]:
        yield nick
    if network._nick_error:
        nick = 'ircperson'
    else:
        nick = network.nicks[0]
    import itertools
    for i in itertools.count(1):
        for j in xrange(len(NICK_SUFFIX)**i):
            suffix = ''.join(NICK_SUFFIX[(j/(len(NICK_SUFFIX)**x))%len(NICK_SUFFIX)] for x in xrange(i))
            if network._nick_max_length:
                yield nick[0:network._nick_max_length-i]+suffix
            else:
                yield nick+suffix

def defRaw(e):
    if not e.done:
        if not e.network.got_nick:
            if e.msg[1] in ('432','433','436','437'): #nickname unavailable
                failednick = e.msg[3]
                nicks = list(e.network.nicks)
                
                if hasattr(e.network,'_nick_generator'):
                    if len(failednick) < len(e.network._next_nick):
                        e.network._nick_max_length = len(failednick)
                    e.network._next_nick = e.network._nick_generator.next()
                    e.network.raw('NICK %s' % e.network._next_nick)
                    e.network._nick_error |= (e.msg[1] == '432')
                else:
                    e.network._nick_error = (e.msg[1] == '432')
                    if len(failednick) < len(e.network.nicks[0]):
                        e.network._nick_max_length = len(failednick)
                    else:
                        e.network._nick_max_length = 0
                    e.network._nick_generator = _nick_generator(e.network)
                    e.network._next_nick = e.network._nick_generator.next()
                    e.network.raw('NICK %s' % e.network._next_nick)
                
                if failednick in nicks[:-1]:
                    index = nicks.index(failednick)+1
                    e.network.raw('NICK %s' % nicks[index])
            
            elif e.msg[1] == '431': #no nickname given--this shouldn't happen
                pass
            
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
                if hasattr(e.network,'_nick_generator'):
                    del e.network._nick_generator, e.network._nick_max_length, e.network._next_nick
                
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
                events.trigger('Connect', e)
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
    e.network.connect_timestamp = time.time()
    if hasattr(e.network,'_nick_generator'):
        del e.network._nick_generator, e.network._nick_max_length, e.network._next_nick

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

def onDisconnect(e):
    if hasattr(e.network,'_reconnect_source'):
        e.network._reconnect_source.unregister()
        del e.network._reconnect_source
    if hasattr(e.network,'connect_timestamp'):
        if e.error and conf.get('autoreconnect',True):
            delay = time.time() - e.network.connect_timestamp > 30 and 30 or 120
            def do_reconnect():
                if not e.network.status:
                    server(network=e.network)
            def do_announce_reconnect():
                if not e.network.status:
                    ui.get_default_window(e.network).write("* Will reconnect in %s seconds.." % delay)
                    e.network._reconnect_source = ui.register_timer(delay*1000,do_reconnect)
            e.network._reconnect_source = ui.register_idle(do_announce_reconnect)

def postDisconnect(e):
    if hasattr(e.network,'connect_timestamp'):
        del e.network.connect_timestamp

def defInput(e):
    if not e.done:
        if e.text.startswith(COMMAND_PREFIX):
            command = e.text[len(COMMAND_PREFIX):]
        else:
            command = 'say - %s' % e.text

        events.run(command, e.window, e.network)
        
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

def defNick(e):
    if e.source != e.network.me:
        window = ui.windows.get(ui.QueryWindow, e.network, e.source)
        if window:
            window.id = e.newnick

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
            e.network.join(' '.join(e.args))
        else:
            raise events.CommandError("We're not connected.")
    elif e.window.role == ui.ChannelWindow:
        e.window.network.join(e.window.id)
    else:
        raise events.CommandError("You must supply a channel.")

#this should be used whereever a new irc.Network may need to be created
def server(server=None,port=6667,network=None,connect=True):
    network_info = {}
    
    if server:
        network_info["name"] = server
        network_info["server"] = server
        if port:
            network_info["port"] = port
        print network_info
        get_network_info(server, network_info)
        print network_info
    
    if not network:
        network = irc.Network(**network_info)
        ui.windows.new(ui.StatusWindow, network, "status").activate()
    else:
        if "server" in network_info:
            network.name = network_info['name']
            network.server = network_info['server']
            if not network.status:
                window = ui.get_default_window(network)
                if window:
                    window.update()
        if "port" in network_info:
            network.port = network_info["port"]
    
    if network.status:
        network.quit()
    if connect:
        network.connect()
        ui.get_default_window(network).write(
            "* Connecting to %s on port %s" % (network.server, network.port)
            )
    
    return network

def onCommandServer(e):
    port = None
    
    if len(e.args):
        host = e.args[0]
        port = 6667
        if ':' in host:
            host, port = host.rsplit(':', 1)
            port = int(port)
            
        elif len(e.args) > 1:
            port = e.args[1]
        
            port = int(port)
    else:
        host = None
    
    if 'm' in e.switches:    
        network = None
    else:
        network = e.network
    
    server(server=host, port=port, network=network, connect='o' not in e.switches)

#see http://www.w3.org/Addressing/draft-mirashi-url-irc-01.txt
def onCommandIrcurl(e):
    url = e.args[0]
    
    if url.startswith('irc://'):
        url = url[6:]
        
        if not url.startswith('/'):
            host, target = url.rsplit('/',1)
            if ':' in host:
                host, port = host.rsplit(':',1)
            else:
                port = 6667
        else:
            host = None
            port = 6667
            target = url
        
        if host:
            if e.network and e.network.server == host:
                network = e.network
            else:
                for w in list(ui.windows):
                    if w.network and w.network.server == host:
                        network = w.network
                        break
                else:
                    for w in list(ui.windows):
                        if w.network and w.network.server == 'irc.default.org':
                            network = server(host,port,w.network)
                            break
                    else:
                        network = server(host,port)
        
        if ',' in target:
            target, modifiers = target.split(',',1)
            action = ''
        else:
            target = unquote(target)
            if target[0] not in '#&+':
                target = '#'+target
            action = 'join %s' % target
        
        if network.status == irc.CONNECTED:
            events.run(action,ui.get_default_window(network),network)
        else:
            if not hasattr(network,'temp_perform'):
                network.temp_perform = [action]
            else:
                network.temp_perform.append(action)

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

needschan = {
    'part':0,
    'topic':0,
    'invite':1,
    'kick':0,
#    'mode':0, #this is commonly used for channels, but can apply to users
#    'names':0, #with no parameters, this is supposed to give a list of all users; we may be able to safely ignore that.
    }
    
def defCommand(e):
    if not e.done: 
        if e.name in needschan and e.window.role == ui.ChannelWindow:
            valid_chan_prefixes = e.network.isupport.get('CHANTYPES', '#&+')
            chan_pos = needschan[e.name]
            
            if len(e.args) > chan_pos:
                if not e.args[chan_pos] or e.args[chan_pos][0] not in valid_chan_prefixes:
                    e.args.insert(chan_pos, e.window.id)
            else:
                e.args.append(e.window.id)
        
        if e.name in trailing:
            trailing_pos = trailing[e.name]
        
            if len(e.args) > trailing_pos:
                e.args[trailing_pos] = ':%s' % e.args[trailing_pos]
        
        e.text = '%s %s' % (e.name, ' '.join(e.args))

def postCommand(e):
    if not e.done and e.network.status >= irc.INITIALIZING:
        e.network.raw(e.text)
        e.done = True
        
def get_network_info(name, network_info):
    conf_info = conf.get('networks', {}).get(name)

    if conf_info:
        network_info['server'] = name
        network_info.update(conf_info)

def onStart(e):
    for network in conf.get('start_networks', []):
        network_info = {'name': network, 'server': network}
        get_network_info(network, network_info)

        nw = irc.Network(**network_info)
        
        ui.windows.new(ui.StatusWindow, nw, 'status').activate()

        nw.connect()

def onConnect(e):
    for command in conf.get('networks', {}).get(e.network.name, {}).get('perform', []):
        events.run(command, e.window, e.network)
    if hasattr(e.network,'temp_perform'):
        for command in e.network.temp_perform:
            events.run(command, e.window, e.network)
        del e.network.temp_perform
