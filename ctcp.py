import time
import events
import copy

import __main__ as urk
import ui

def ctcp(network, user, msg):
    param_list = msg.split(' ')
    param_list[0] = param_list[0].upper()
    network.raw('PRIVMSG %s :\x01%s\x01' % (user,' '.join(param_list)))

def ctcp_reply(network, user, msg):
    param_list = msg.split(' ')
    param_list[0] = param_list[0].upper()
    network.raw('NOTICE %s :\x01%s\x01' % (user,' '.join(param_list)))

def emote(network, user, msg):
    network.raw("PRIVMSG %s :\x01ACTION %s\x01" % (user, msg))
    e_data = events.data()
    e_data.source = network.me
    e_data.target = str(user)
    e_data.text = msg
    e_data.network = network
    e_data.window = ui.get_status_window(network)
    events.trigger('OwnAction', e_data)

def defCommand(event):
    if not event.done:
        if event.name == 'me':
            if type(event.window) in (ui.ChannelWindow, ui.QueryWindow):
                emote(event.network, event.window.id, ' '.join(event.args))
                event.done = True
            else:
                event.error_text = "There's no one here to speak to."
        elif event.name == 'ctcp':
            ctcp(event.network, event.args[0], ' '.join(event.args[1:]))
            event.done = True
        elif event.name == 'ping':
            ctcp(event.network, event.args[0], 'PING %s' % time.time())
            event.done = True
        elif event.name == 'ctcpreply':
            ctcp_reply(event.network, event.args[0], ' '.join(event.args[1:]))
            event.done = True

def setupText(event):
    if event.text[0] == '\x01' and event.text[-1] == '\x01':
        e_data = copy.copy(event)
        e_data.text = event.text[1:-1]
        tokens = e_data.text.split(' ')
        e_data.name = tokens[0]
        e_data.args = tokens[1:]
        events.trigger('Ctcp', e_data)
        events.halt()

def setupNotice(event):
    if event.text[0] == '\x01' and event.text[-1] == '\x01':
        e_data = copy.copy(event)
        e_data.text = event.text[1:-1]
        tokens = e_data.text.split(' ')
        e_data.name = tokens[0]
        e_data.args = tokens[1:]
        events.trigger('CtcpReply', e_data)
        events.halt()

def preCtcpReply(event):
    if event.name == 'PING':
        try:
            elapsed_time = "%0.2f seconds" % (time.time() - float(event.args[0]))
            event.old_args = event.args
            event.args = [elapsed_time]
        except:
            pass

def defCtcp(event):
    if not event.done:
        if event.name == 'ACTION':
            e_data = copy.copy(event)
            e_data.text = ' '.join(event.args)
            events.trigger('Action', e_data)
            event.done = True
            event.quiet = True
        elif event.name == 'PING':
            ctcp_reply(event.network, event.source, event.text)
            event.done = True
        elif event.name == 'VERSION':
            ctcp_reply(event.network, event.source, 'VERSION %s' % urk.long_version)
            event.done = True
        elif event.name == 'TIME':
            ctcp_reply(event.network, event.source, 'TIME %s' % time.asctime())
            event.done = True

events.load(__name__)
