import copy

import events
import ui
import irc

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
        
        elif e.msg[1] == "376": #RPL_ENDOFMOTD
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
