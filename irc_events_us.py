import copy

import events
import ui
import irc

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
                
        if event.msg[1] == "PING":
            event.network.raw("PONG :%s" % event.msg[-1])
            event.done = True
            event.quiet = True
        
        elif event.msg[1] in ("JOIN", "PART", "MODE"):
            event.channel = event.target
            event.text = ' '.join(event.msg[3:])
            events.trigger(event.msg[1].capitalize(), event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "QUIT":
            events.trigger('Quit', event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "KICK":
            event.channel = event.msg[2]
            event.target = event.msg[3]
            events.trigger('Kick', event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "NICK":
            event.newnick = event.msg[2]
            events.trigger('Nick', event)
            if event.network.me == event.source:
                event.network.me = event.newnick

            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "PRIVMSG":
            events.trigger('Text', event)
            event.done = True
            event.quiet = True
        
        elif event.msg[1] == "NOTICE":
            events.trigger('Notice', event)
            event.done = True
            event.quiet = True
        
        elif event.msg[1] == "TOPIC":
            events.trigger('Topic', event)
            event.done = True
            event.quiet = True
        
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

def setupDisconnect(event):
    if not hasattr(event, 'window'):
        event.window = ui.get_status_window(event.network)
