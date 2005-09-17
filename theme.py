import pango
import gtk

import ui
import events

import chaninfo

textareas = {
    'bg': '#2E3D49',
    'fg': '#DEDEDE',
    'font': 'sans 8',
    }

ui.set_style("view", textareas)
ui.set_style("nicklist", textareas)

def onText(event):
    color = "\x02\x040000CC"
    if event.network.me == event.target:
        if event.window.id == event.network.norm_case(event.source):
            format = "%s<\x0F%s%s>\x0F %s"
        else:
            format = "%s*\x0F%s%s*\x0F %s"
        to_write = format % (color, event.source, color, event.text)
    else:
        if event.window.id == event.network.norm_case(event.target):
            to_write = "%s<\x0F%s%s>\x0F %s" % (color, event.source, color, event.text)
        else:
            to_write = "%s*\x0F%s:%s%s*\x0F %s" % (color, event.source, event.target, color, event.text)
    
    event.window.write(to_write, ui.TEXT)
    
def onOwnText(event):
    color = "\x02\x04FF00FF"
    if event.window.id == event.network.norm_case(event.target):
        to_write = "%s<\x0F%s%s>\x0F %s" % (color, event.source, color, event.text)
    else:
        to_write = "%s-> *\x0F%s%s*\x0F %s" % (color, event.target, color, event.text)
    
    event.window.write(to_write)
    
def onAction(event):
    color = '\x02\x040000CC'
    to_write = "%s*\x0F %s %s" % (color, event.source, event.text)
    
    event.window.write(to_write, ui.TEXT)

def onOwnAction(event):
    color = '\x02\x04FF00FF'
    to_write = "%s*\x0F %s %s" % (color, event.source, event.text)
    
    event.window.write(to_write)

def onNotice(event):
    to_write = "\x02\x040000CC-\x0F%s\x02\x040000CC-\x0F %s" % (event.source, event.text)
    
    if not event.quiet:
        window = ui.windows.manager.get_active()
        if window.network != event.network:
            window = ui.get_status_window(event.network)
        window.write(to_write, ui.TEXT)

def onOwnNotice(event):
    to_write = "\x02\x04FF00FF-> -\x0F%s\x02\x04FF00FF-\x0F %s" % (event.target, event.text)
    
    event.window.write(to_write)

def onCtcp(event):
    to_write = "\x02\x040000CC[\x0F%s\x02\x040000CC]\x0F %s" % (event.source, event.text)
    
    event.window.write(to_write)

def onCtcpReply(event):
    to_write = "--- %s reply from %s: %s" % (event.name.capitalize(), event.source, ' '.join(event.args))
    
    window = ui.windows.manager.get_active()
    if window.network != event.network:
        window = ui.get_status_window(event.network)
    window.write(to_write, ui.TEXT)

def onJoin(event):
    if event.network.me == event.source:
        to_write = "\x02You\x02 joined %s" % event.target
    else:
        to_write = "\x02%s\x02 (%s) joined %s" % (event.source, event.address, event.target)
    
    event.window.write(to_write)
        
def onPart(event):
    if event.network.me == event.source:
        to_write = "\x02You\x02 left %s" % event.target
    else:
        to_write = "\x02%s\x02 (%s) left %s" % (event.source, event.address, event.target)
    if event.text:
        to_write += ' (%s)' % event.text
    
    event.window.write(to_write)

def onKick(event):
    to_write = "\x02%s\x02 kicked %s (%s)" % (event.source, event.target, event.text)
    
    event.window.write(to_write)
        
def onMode(event):
    to_write = "\x02%s\x02 sets mode: %s" % (event.source, event.text)
    
    event.window.write(to_write)
        
def onQuit(event):
    to_write = "\x02%s\x02 quit (%s)" % (event.source, event.text)
    
    for channame in event.network.channels:
        if event.source in event.network.channels[channame].nicks:
            window = ui.windows.get(ui.ChannelWindow, event.network, channame)
            if window:
                window.write(to_write)

def onNick(event):
    if event.source == event.network.me:
        to_write = "\x02You\x02 are now known as %s" % event.newnick
    else:
        to_write = "\x02%s\x02 is now known as %s" % (event.source, event.newnick)
    
    for channame in event.network.channels:
        if event.source in event.network.channels[channame].nicks:
            window = ui.windows.get(ui.ChannelWindow, event.network, channame)
            if window:
                window.write(to_write)

    if event.source == event.network.me:
        window = ui.get_status_window(event.network)
        if window:
            window.write(to_write)

def onTopic(event):
    to_write = "\x02%s\x02 set topic on %s: %s" % (event.source, event.target, event.text)
    
    event.window.write(to_write)

def onRaw(event):
    if not event.quiet:
        if event.msg[1].isdigit():
            if event.msg[1] == '332':
                window = ui.windows.get(ui.ChannelWindow, event.network, event.msg[3]) or event.window
                window.write("topic on %s is: %s" % (event.msg[3], event.text))
                
            else:
                event.window.write("* %s" % ' '.join(event.msg[3:]))
        elif event.msg[1] == 'ERROR':
            event.window.write("Error: %s" % event.text)

def onDisconnect(event):
    if event.error:
        to_write = '* Disconnected (%s)' % event.error
    else:
        to_write = '* Disconnected'

    for window in ui.get_window_for(network=event.network):
        window.write(to_write, (type(window) == ui.StatusWindow and ui.TEXT) or ui.EVENT)
