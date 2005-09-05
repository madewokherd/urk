import time

import __main__ as urk

def defCommand(event):
    if not event.done and event.name == 'ping':
        event.network.ctcp(event.args[0], 'PING %s' % time.time())
        event.done = True

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
        if event.name == 'PING':
            event.network.ctcp_reply(event.source, event.text)
            event.done = True
        elif event.name == 'VERSION':
            event.network.ctcp_reply(event.source, 'VERSION %s' % urk.long_version)
            event.done = True
        elif event.name == 'TIME':
            event.network.ctcp_reply(event.source, 'TIME %s' % time.asctime())
            event.done = True
