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
                    e_data.type = 'nick'
                    events.trigger('Nick', e_data)
                    event.network.me = event.msg[2]
                
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
                ui.window.nick_label.update()

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
        
        elif event.msg[1] == "NOTICE":
            if event.text[0] == '\x01' and event.text[-1] == '\x01':
                e_data = copy.copy(event)
                e_data.type = 'ctcp_reply'
                e_data.text = event.text[1:-1]
                tokens = e_data.text.split(' ')
                e_data.name = tokens[0]
                e_data.args = tokens[1:]
                events.trigger('CtcpReply', e_data)
            else:
                event.type = "notice"
                events.trigger('Notice', event)
            event.done = True
            event.quiet = True
        
        elif event.msg[1] == "TOPIC":
            event.type = "topic"
            events.trigger('Topic', event)
            event.done = True
            event.quiet = True
        
        elif event.msg[1] == "376": #RPL_ENDOFMOTD
            if event.network.status == irc.INITIALIZING:
                event.network.status = irc.CONNECTED
                e_data = copy.copy(event)
                e_data.type = 'connect'
                events.trigger('Connect', e_data)
            event.done = True

def setupSocketConnect(event):
    event.network.got_nick = False

def setupDisconnect(event):
    if not hasattr(event, 'window'):
        event.window = ui.get_status_window(event.network)
    
    event.type = "disconnect"

def defCtcp(event):
    if not event.done:
        if event.name == 'ACTION':
            e_data = copy.copy(event)
            e_data.type = 'action'
            e_data.text = ' '.join(event.args)
            events.trigger('Action', e_data)
        event.done = True
