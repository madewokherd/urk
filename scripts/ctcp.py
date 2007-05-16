import time

import events
import urk
import windows

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
    events.trigger(
        'OwnAction', network=network, window=windows.get_default(network),
        source=network.me, target=str(user), text=msg
        )

def onCommandMe(e):
    if isinstance(e.window, windows.ChannelWindow) or isinstance(e.window, windows.QueryWindow):
        #kludge around switches so we don't lose the -> in /me -> something
        #emote(e.network, e.window.id, ' '.join(e.args))
        command, text = e.text.split(" ",1)
        emote(e.network, e.window.id, text)
    else:
        raise events.CommandError("There's no one here to speak to.")

def onCommandCtcp(e):
    ctcp(e.network, e.args[0], ' '.join(e.args[1:]))

def onCommandPing(e):
    ctcp(e.network, e.args[0], 'PING %s' % time.time())

def onCommandCtcpreply(e):
    ctcp_reply(e.network, e.args[0], ' '.join(e.args[1:]))

def setupRaw(e):
    if not e.done and e.msg[1] in ('PRIVMSG', 'NOTICE') and \
          e.text.startswith('\x01') and e.text.endswith('\x01'):
        e_data = events.data(**e.__dict__)
        e_data.text = e.text[1:-1]
        tokens = e_data.text.split(' ')
        e_data.name = tokens[0].upper()
        e_data.args = tokens[1:]
        if e.msg[1] == 'PRIVMSG':
            events.trigger('Ctcp', e_data)
        else:
            events.trigger('CtcpReply', e_data)
        e.done = True

def setupCtcpReply(e):
    if e.name == 'PING':
        try:
            elapsed_time = "%0.2f seconds" % (time.time() - float(e.args[0]))
            e.old_args = e.args
            e.args = [elapsed_time]
        except:
            pass

def setupCtcp(e):
    if not e.done:
        if e.name == 'ACTION':
            e_data = events.data(**e.__dict__)
            e_data.text = ' '.join(e.args)
            events.trigger('Action', e_data)
            e.done = True
            e.quiet = True
        elif e.name == 'PING':
            ctcp_reply(e.network, e.source, e.text)
            e.done = True
        elif e.name == 'VERSION':
            ctcp_reply(e.network, e.source, 'VERSION %s - %s' % (urk.long_version, urk.website))
            e.done = True
        elif e.name == 'TIME':
            ctcp_reply(e.network, e.source, 'TIME %s' % time.asctime())
            e.done = True

events.load(__name__)
