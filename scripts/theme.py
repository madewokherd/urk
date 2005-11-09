import time

import ui
import chaninfo
import events

textareas = {
    'bg': '#2E3D49',
    'fg': '#DEDEDE',
    'font': 'sans 8',
    }

ui.set_style("view", textareas)
ui.set_style("nicklist", textareas)

#take an event e, trigger the highlight event if necessary, and return a
# (formatted) string
def hilight_text(e):
    if not hasattr(e,"hilight"):
        e.hilight = []
        events.trigger("Hilight",e)

#hilight own nick
def onHilight(e):
    pos = e.text.find(e.network.me,0)
    while pos != -1:
        e.hilight.append((pos,pos+len(e.network.me)))
        pos = e.text.find(e.network.me,pos+1)

def prefix(e):
    #return time.strftime('[%H:%M] ')
    return ""

def format_source(e):
    if e.hilight:
        return "\x02\x04EEDD22%s\x0F" % e.source
    else:
        return e.source

def format_info_source(e):
    if e.source == e.network.me:
        return "\x02You\x02"
    else:
        return "\x02%s\x02" % e.source

def address(e):
    if e.source != e.network.me:
        return "(%s) " % e.address
    else:
        return ""

def text(e):
    if e.text:
        return " (%s\x0F)" % e.text
    else:
        return ""

def onText(e):
    hilight_text(e)
    color = "\x02\x040000CC"
    to_write = prefix(e)
    if e.network.me == e.target:    # this is a pm
        if e.window.id == e.network.norm_case(e.source):
            to_write += "%s<\x0F%s%s>\x0F " % (color, format_source(e), color)
        else:
            to_write += "%s*\x0F%s%s*\x0F " % (color, format_source(e), color)
    else:
        if e.window.id == e.network.norm_case(e.target):
            to_write += "%s<\x0F%s%s>\x0F " % (color, format_source(e), color)
        else:
            to_write += "%s<\x0F%s:%s%s>\x0F " % (color, format_source(e), e.target, color)
    to_write += e.text
    
    if e.hilight:
        e.window.write(to_write, ui.HILIT)
    else:
        e.window.write(to_write, ui.TEXT)
    
def onOwnText(e):
    color = "\x02\x04FF00FF"
    to_write = prefix(e)
    if e.window.id == e.network.norm_case(e.target):
        to_write += "%s<\x0F%s%s>\x0F %s" % (color, e.source, color, e.text)
    else:
        to_write += "%s-> *\x0F%s%s*\x0F %s" % (color, e.target, color, e.text)
    
    e.window.write(to_write)
    
def onAction(e):
    hilight_text(e)
    color = "\x02\x040000CC"
    to_write = "%s%s*\x0F %s %s" % (prefix(e), color, format_source(e), e.text)
    
    if e.hilight:
        e.window.write(to_write, ui.HILIT)
    else:
        e.window.write(to_write, ui.TEXT)
    
def onOwnAction(e):
    color = '\x02\x04FF00FF'
    to_write = "%s%s*\x0F %s %s" % (prefix(e), color, e.source, e.text)
    
    e.window.write(to_write)

def onNotice(e):
    hilight_text(e)
    color = "\x02\x040000CC"
    to_write = "%s%s-\x0F%s%s-\x0F %s" % (prefix(e), color, e.source, color, e.text)
    
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
    window.write(to_write, (e.hilight and ui.HILIT) or ui.TEXT)

def onOwnNotice(e):
    to_write = "%s\x02\x04FF00FF-> -\x0F%s\x02\x04FF00FF-\x0F %s" % (prefix(e), e.target, e.text)
    
    e.window.write(to_write)

def onCtcp(e):
    to_write = "%s\x02\x040000CC[\x0F%s\x02\x040000CC]\x0F %s" % (prefix(e), e.source, e.text)
    
    if not e.quiet:
        e.window.write(to_write)

def onCtcpReply(e):
    to_write = "%s--- %s reply from %s: %s" % (prefix(e), e.name.capitalize(), e.source, ' '.join(e.args))
    
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
    window.write(to_write, ui.TEXT)

def onJoin(e):
    to_write = "%s%s %sjoined %s" % (prefix(e), format_info_source(e), address(e), e.target)
    
    e.window.write(to_write)
        
def onPart(e):
    to_write = "%s%s %sleft %s%s" % (prefix(e), format_info_source(e), address(e), e.target, text(e))
    
    e.window.write(to_write)

def onKick(e):
    to_write = "%s%s kicked %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    
    e.window.write(to_write, (e.target == e.network.me and ui.TEXT) or ui.EVENT)
        
def onMode(e):
    to_write = "%s%s sets mode: %s" % (prefix(e), format_info_source(e), e.text)
    
    e.window.write(to_write)
        
def onQuit(e):
    to_write = "%s%s quit%s" % (prefix(e), format_info_source(e), text(e))
    
    for channame in chaninfo.channels(e.network):
        if chaninfo.ison(e.network, channame, e.source):
            window = ui.windows.get(ui.ChannelWindow, e.network, channame)
            if window:
                window.write(to_write)

def onNick(e):
    if e.source == e.network.me:
        to_write = "%s\x02You\x02 are now known as %s" % (prefix(e), e.newnick)
    else:
        to_write = "%s\x02%s\x02 is now known as %s" % (prefix(e), e.source, e.newnick)
    
    if e.source == e.network.me:
        for window in ui.get_window_for(network=e.network):
            window.write(to_write)
    else:
        for channame in chaninfo.channels(e.network):
            if chaninfo.ison(e.network,channame,e.source):
                window = ui.windows.get(ui.ChannelWindow, e.network, channame)
                if window:
                    window.write(to_write)

def onTopic(e):
    to_write = "%s%s set topic on %s: %s" % (prefix(e), format_info_source(e), e.target, e.text)
    
    e.window.write(to_write)

def onRaw(e):
    if not e.quiet:
        if e.msg[1].isdigit():
            if e.msg[1] == '332':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                window.write("%stopic on %s is: %s" % (prefix(e), e.msg[3], e.text))
                
            elif e.msg[1] == '333':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                window.write("%stopic on %s set by %s at time %s" % (prefix(e), e.msg[3], e.msg[4], time.ctime(int(e.msg[5]))))
            
            elif e.msg[1] == '329': #RPL_CREATIONTIME
                pass
            
            else:
                e.window.write("* %s" % ' '.join(e.msg[3:]))
        elif e.msg[1] == 'ERROR':
            e.window.write("Error: %s" % e.text)

def onDisconnect(e):
    to_write = '%s* Disconnected' % prefix(e)
    if e.error:
        to_write += ' (%s)' % e.error

    for window in ui.get_window_for(network=e.network):
        window.write(to_write, (window.role == ui.StatusWindow and ui.TEXT) or ui.EVENT)
