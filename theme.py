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

def onText(e):
    color = "\x02\x040000CC"
    if e.network.me == e.target:
        if e.window.id == e.network.norm_case(e.source):
            format = "%s<\x0F%s%s>\x0F %s"
        else:
            format = "%s*\x0F%s%s*\x0F %s"
        to_write = format % (color, e.source, color, e.text)
    else:
        if e.window.id == e.network.norm_case(e.target):
            to_write = "%s<\x0F%s%s>\x0F %s" % (color, e.source, color, e.text)
        else:
            to_write = "%s*\x0F%s:%s%s*\x0F %s" % (color, e.source, e.target, color, e.text)
    
    e.window.write(to_write, ui.TEXT)
    
def onOwnText(e):
    color = "\x02\x04FF00FF"
    if e.window.id == e.network.norm_case(e.target):
        to_write = "%s<\x0F%s%s>\x0F %s" % (color, e.source, color, e.text)
    else:
        to_write = "%s-> *\x0F%s%s*\x0F %s" % (color, e.target, color, e.text)
    
    e.window.write(to_write)
    
def onAction(e):
    color = '\x02\x040000CC'
    to_write = "%s*\x0F %s %s" % (color, e.source, e.text)
    
    e.window.write(to_write, ui.TEXT)

def onOwnAction(e):
    color = '\x02\x04FF00FF'
    to_write = "%s*\x0F %s %s" % (color, e.source, e.text)
    
    e.window.write(to_write)

def onNotice(e):
    to_write = "\x02\x040000CC-\x0F%s\x02\x040000CC-\x0F %s" % (e.source, e.text)
    
    if not e.quiet:
        window = ui.windows.manager.get_active()
        if window.network != e.network:
            window = ui.get_default_window(e.network)
        window.write(to_write, ui.TEXT)

def onOwnNotice(e):
    to_write = "\x02\x04FF00FF-> -\x0F%s\x02\x04FF00FF-\x0F %s" % (e.target, e.text)
    
    e.window.write(to_write)

def onCtcp(e):
    to_write = "\x02\x040000CC[\x0F%s\x02\x040000CC]\x0F %s" % (e.source, e.text)
    
    e.window.write(to_write)

def onCtcpReply(e):
    to_write = "--- %s reply from %s: %s" % (e.name.capitalize(), e.source, ' '.join(e.args))
    
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
    window.write(to_write, ui.TEXT)

def onJoin(e):
    if e.network.me == e.source:
        to_write = "\x02You\x02 joined %s" % e.target
    else:
        to_write = "\x02%s\x02 (%s) joined %s" % (e.source, e.address, e.target)
    
    e.window.write(to_write)
        
def onPart(e):
    if e.network.me == e.source:
        to_write = "\x02You\x02 left %s" % e.target
    else:
        to_write = "\x02%s\x02 (%s) left %s" % (e.source, e.address, e.target)
    if e.text:
        to_write += ' (%s)' % e.text
    
    e.window.write(to_write)

def onKick(e):
    to_write = "\x02%s\x02 kicked %s (%s)" % (e.source, e.target, e.text)
    
    e.window.write(to_write)
        
def onMode(e):
    to_write = "\x02%s\x02 sets mode: %s" % (e.source, e.text)
    
    e.window.write(to_write)
        
def onQuit(e):
    to_write = "\x02%s\x02 quit (%s)" % (e.source, e.text)
    
    for channame in e.network.channels:
        if e.source in e.network.channels[channame].nicks:
            window = ui.windows.get(ui.ChannelWindow, e.network, channame)
            if window:
                window.write(to_write)

def onNick(e):
    if e.source == e.network.me:
        to_write = "\x02You\x02 are now known as %s" % e.newnick
    else:
        to_write = "\x02%s\x02 is now known as %s" % (e.source, e.newnick)
    
    for channame in e.network.channels:
        if e.source in e.network.channels[channame].nicks:
            window = ui.windows.get(ui.ChannelWindow, e.network, channame)
            if window:
                window.write(to_write)

    if e.source == e.network.me:
        window = ui.get_default_window(e.network)
        if window:
            window.write(to_write)

def onTopic(e):
    to_write = "\x02%s\x02 set topic on %s: %s" % (e.source, e.target, e.text)
    
    e.window.write(to_write)

def onRaw(e):
    if not e.quiet:
        if e.msg[1].isdigit():
            if e.msg[1] == '332':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                window.write("topic on %s is: %s" % (e.msg[3], e.text))
                
            else:
                e.window.write("* %s" % ' '.join(e.msg[3:]))
        elif e.msg[1] == 'ERROR':
            e.window.write("Error: %s" % e.text)

def onDisconnect(e):
    if e.error:
        to_write = '* Disconnected (%s)' % e.error
    else:
        to_write = '* Disconnected'

    for window in ui.get_window_for(network=e.network):
        window.write(to_write, (type(window) == ui.StatusWindow and ui.TEXT) or ui.e)
