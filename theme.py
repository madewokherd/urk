import pango
import gtk

import ui
import events

events.load('irc_basicinfo')

viewstyle = {
    'bg': '#2E3D49',
    'fg': '#DEDEDE',
    'font': 'sans 8',
    }

ui.set_viewstyle(viewstyle)

def onText(event):
    color = (event.network.me == event.source and "\x02\x04FF00FF") or "\x02\x040000CC"
    if event.network.me == event.target:
        if event.window.id == event.network.normalize_case(event.source):
            format = "%s<\x0F%s%s>\x0F %s"
        else:
            format = "%s*\x0F%s%s*\x0F %s"
        to_write = format % (color, event.source, color, event.text)
    else:
        if event.window.id == event.network.normalize_case(event.target):
            to_write = "%s<\x0F%s%s>\x0F %s" % (color, event.source, color, event.text)
        else:
            to_write = "%s-> *\x0F%s%s*\x0F %s" % (color, event.target, color, event.text)
    
    if not event.quiet:
        event.window.write(to_write, ui.TEXT)
    
def onAction(event):
    if event.network.me == event.source:
        color = '\x02\x04FF00FF'
    else:
        color = '\x02\x040000CC'
    to_write = "%s*\x0F %s %s" % (color, event.source, event.text)
    
    if not event.quiet:
        event.window.write(to_write, ui.TEXT)

def onNotice(event):
    to_write = "\x02\x040000CC-\x0F%s\x02\x040000CC-\x0F %s" % (event.source, event.text)
    
    if not event.quiet:
        window = ui.get_active()
        if window.network != event.network:
            window = ui.get_status_window(event.network)
        window.write(to_write, ui.TEXT)

def onOwnNotice(event):
    to_write = "\x02\x04FF00FF-> -\x0F%s\x02\x04FF00FF-\x0F %s" % (event.target, event.text)
    
    if not event.quiet:
        event.window.write(to_write)

def onJoin(event):
    if event.network.me == event.source:
        to_write = "\x02You\x02 joined %s" % event.target
    else:
        to_write = "\x02%s\x02 (%s) joined %s" % (event.source, event.address, event.target)
    
    if not event.quiet:
        event.window.write(to_write)
        
def onPart(event):
    if event.network.me == event.source:
        to_write = "\x02You\x02 left %s" % event.target
    else:
        to_write = "\x02%s\x02 (%s) left %s" % (event.source, event.address, event.target)
    
    if not event.quiet:
        event.window.write(to_write)

def onKick(event):
    to_write = "\x02%s\x02 kicked %s (%s)" % (event.source, event.target, event.text)
    
    if not event.quiet:
        event.window.write(to_write)
        
def onMode(event):
    to_write = "\x02%s\x02 sets mode: %s" % (event.source, event.text)
    
    if not event.quiet:
        event.window.write(to_write)
        
def onQuit(event):
    to_write = "\x02%s\x02 (%s) quit (%s)" % (event.source, event.address, event.text)
    
    if not event.quiet:
        for channame in event.network.channels:
            if event.source in event.network.channels[channame].nicks:
                window = ui.window_list[event.network, 'channel', channame]
                if window:
                    window.write(to_write)

def onNick(event):
    if event.source == event.network.me:
        to_write = "\x02You\x02 are now known as %s" % event.newnick
    else:
        to_write = "\x02%s\x02 is now known as %s" % (event.source, event.newnick)
    
    if not event.quiet:
        for channame in event.network.channels:
            if event.source in event.network.channels[channame].nicks:
                window = ui.window_list[event.network, 'channel', channame]
                if window:
                    window.write(to_write)

def onTopic(event):
    to_write = "\x02%s\x02 set topic on %s: %s" % (event.source, event.target, event.text)
    
    if not event.quiet:
        event.window.write(to_write)

def onRaw(event):
    if not event.quiet:
        if event.msg[1] == '332':
            window = ui.window_list[event.network, 'channel', event.msg[3]] or event.window
            window.write("topic on %s is: %s" % (event.msg[3], event.text))
        else:
            event.window.write("* %s %s" % (event.source, event.text))

def onDisconnect(event):
    if event.error:
        to_write = '* Disconnected (%s)' % event.error
    else:
        to_write = '* Disconnected'
    for network, type, id in ui.window_list:
        if network == event.network:
            ui.window_list[network, type, id].write(to_write, (type == 'status' and ui.TEXT) or ui.EVENT)
