import copy

import events
import ui
import __main__ as urk

def defRaw(event):
    if not event.done:
        if not event.network.me:
            if event.msg[1] == '001':
                event.network.me = event.msg[2]
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
        
        elif event.msg[1] in ("JOIN", "PART", "MODE"):
            event.channel = event.target
            event.type = event.msg[1].lower()
            event.text = ' '.join(event.msg[3:])
            events.trigger(event.msg[1].capitalize(), event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "QUIT":
            event.type = 'quit'
            events.trigger('Quit', event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "KICK":
            event.type = 'kick'
            event.channel = event.msg[2]
            event.target = event.msg[3]
            events.trigger('Kick', event)
            event.done = True
            event.quiet = True
            
        elif event.msg[1] == "NICK":
            event.type = 'nick'
            event.newnick = event.msg[2]
            events.trigger('Nick', event)
            if event.network.me == event.source:
                event.network.me = event.newnick
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
        
        elif event.msg[1] == "376": #RPL_ENDOFMOTD
            if not event.network.connected:
                event.network.connected = True
                e_data = copy.copy(event)
                e_data.type = 'connect'
                events.trigger('Connect', e_data)
            event.done = True

def setupDisconnect(event):
    if not hasattr(event, 'window'):
        event.window = urk.get_window[event.network]
    
    event.network.connected = False
    
    event.type = "disconnect"

def defCtcp(event):
    if not event.done:
        if event.name == 'ACTION':
            e_data = copy.copy(event)
            e_data.type = 'action'
            e_data.text = ' '.join(event.args)
            events.trigger('Action', e_data)
        event.done = True
