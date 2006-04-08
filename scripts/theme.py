import time

import windows
import widgets
import chaninfo
import events
from conf import conf

textareas = {
    'bg': '#2E3D49',
    'fg': '#DEDEDE',
    'font': conf.get('font', 'sans 8'),
    }

widgets.set_style("view", textareas)
widgets.set_style("nicklist", textareas)

#take an event e and trigger the highlight event if necessary
def hilight_text(e):
    if not hasattr(e, 'hilight'):
        e.hilight = []
        events.trigger('Hilight', e)

#hilight own nick
def onHilight(e):
    for word in conf.get('highlight_words', []) + [e.network.me]:
        pos = e.text.find(word,0)
        while pos != -1:
            e.hilight.append((pos, pos+len(word)))
            pos = e.text.find(word, pos+1)

def prefix(e):
    return time.strftime(conf.get('timestamp', ''))

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
        return "%s " % info_in_brackets(e.address)
    else:
        return ""

def text(e):
    if e.text:
        return " %s" % info_in_brackets(e.text)
    else:
        return ""
        
def info_in_brackets(text):
    return "\x04777777(\x0400CCCC%s\x04777777)\x0F" % text

def pretty_time(secs):
    times = (
        #("years", "year", 31556952),
        ("weeks", "week", 604800),
        ("days", "day", 86400),
        ("hours", "hour", 3600),
        ("minutes", "minute", 60),
        ("seconds", "second", 1),
        )
    if secs == 0:
        return "0 seconds"
    result = ""
    for plural, singular, amount in times:
        n, secs = divmod(secs, amount)
        if n == 1:
            result = result + " %s %s" % (n, singular)
        elif n:
            result = result + " %s %s" % (n, plural)
    return result[1:]

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
        e.window.write(to_write, widgets.HILIT)
    else:
        e.window.write(to_write, widgets.TEXT)
    
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
        e.window.write(to_write, widgets.HILIT)
    else:
        e.window.write(to_write, widgets.TEXT)
    
def onOwnAction(e):
    color = '\x02\x04FF00FF'
    to_write = "%s%s*\x0F %s %s" % (prefix(e), color, e.source, e.text)
    
    e.window.write(to_write)

def onNotice(e):
    hilight_text(e)
    color = "\x02\x040000CC"
    to_write = prefix(e)
    if e.network.me == e.target:    # this is a pm
        to_write += "%s-\x0F%s%s-\x0F " % (color, format_source(e), color)
    else:
        to_write += "%s-\x0F%s:%s%s-\x0F " % (color, format_source(e), e.target, color)
    to_write += e.text
    
    e.window.write(to_write, (e.hilight and widgets.HILIT) or widgets.TEXT)

def onOwnNotice(e):
    to_write = "%s\x02\x04FF00FF-> -\x0F%s\x02\x04FF00FF-\x0F %s" % (prefix(e), e.target, e.text)
    
    e.window.write(to_write)

def onCtcp(e):
    to_write = "%s\x02\x040000CC[\x0F%s\x02\x040000CC]\x0F %s" % (prefix(e), e.source, e.text)
    
    if not e.quiet:
        e.window.write(to_write)

def onCtcpReply(e):
    to_write = "%s--- %s reply from %s: %s" % (prefix(e), e.name.capitalize(), e.source, ' '.join(e.args))
    
    window = windows.manager.get_active()
    if window.network != e.network:
        window = windows.get_default(e.network)
    window.write(to_write, widgets.TEXT)

def onJoin(e):
    to_write = "%s%s %sjoined %s" % (prefix(e), format_info_source(e), address(e), e.target)
    
    e.window.write(to_write)
        
def onPart(e):
    #to_write = "%s%s %sleft %s%s" % (prefix(e), format_info_source(e), address(e), e.target, text(e))
    to_write = "%s%s left %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    
    e.window.write(to_write)

def onKick(e):
    to_write = "%s%s kicked %s%s" % (prefix(e), format_info_source(e), e.target, text(e))
    
    e.window.write(to_write, (e.target == e.network.me and widgets.HILIT) or widgets.EVENT)
        
def onMode(e):
    if e.source == e.network.me:
        to_write = "%s\x02You\x02 set mode: %s" % (prefix(e), e.text)
    else:
        to_write = "%s%s sets mode: %s" % (prefix(e), format_info_source(e), e.text)
    
    e.window.write(to_write)
        
def onQuit(e):
    to_write = "%s%s quit%s" % (prefix(e), format_info_source(e), text(e))
    
    for channame in chaninfo.channels(e.network):
        if chaninfo.ison(e.network, channame, e.source):
            window = windows.get(windows.ChannelWindow, e.network, channame)
            if window:
                window.write(to_write)

def onNick(e):
    if e.source == e.network.me:
        to_write = "%sYou are now known as \x02%s\x02" % (prefix(e), e.target)
    else:
        to_write = "%s%s is now known as \x02%s\x02" % (prefix(e), e.source, e.target)
    
    if e.source == e.network.me:
        for window in windows.get_with(network=e.network):
            window.write(to_write)
    else:
        for channame in chaninfo.channels(e.network):
            if chaninfo.ison(e.network,channame,e.source):
                window = windows.get(windows.ChannelWindow, e.network, channame)
                if window:
                    window.write(to_write)

def onTopic(e):
    to_write = "%s%s set topic on %s: %s" % (prefix(e), format_info_source(e), e.target, e.text)
    
    e.window.write(to_write)

def onRaw(e):
    if not e.quiet:
        if e.msg[1].isdigit():
            if e.msg[1] == '332':
                window = windows.get(windows.ChannelWindow, e.network, e.msg[3]) or e.window
                window.write(
                    "%sTopic on %s is: %s" % 
                        (prefix(e), e.msg[3], e.text)
                        )
                
            elif e.msg[1] == '333':
                window = windows.get(windows.ChannelWindow, e.network, e.msg[3]) or e.window
                window.write(
                    "%sTopic on %s set by %s at time %s" % 
                        (prefix(e), e.msg[3], e.msg[4], time.ctime(int(e.msg[5])))
                        )
            
            elif e.msg[1] == '329': #RPL_CREATIONTIME
                pass
            
            elif e.msg[1] == '311': #RPL_WHOISUSER
                e.window.write("* %s is %s@%s * %s" % (e.msg[3], e.msg[4], e.msg[5], e.msg[7]))
            
            elif e.msg[1] == '312': #RPL_WHOISSERVER
                e.window.write("* %s on %s (%s)" % (e.msg[3], e.msg[4], e.msg[5]))
            
            elif e.msg[1] == '317': #RPL_WHOISIDLE
                e.window.write("* %s has been idle for %s" % (e.msg[3], pretty_time(int(e.msg[4]))))
                if e.msg[5].isdigit():
                    e.window.write("* %s signed on %s" % (e.msg[3], time.ctime(int(e.msg[5]))))
            
            elif e.msg[1] == '319': #RPL_WHOISCHANNELS
                e.window.write("* %s on channels: %s" % (e.msg[3], e.msg[4]))
            
            elif e.msg[1] == '330': #RPL_WHOISACCOUNT
                #this appears to conflict with another raw, so if there's anything weird about it,
                # we fall back on the default
                if len(e.msg) == 6 and not e.msg[4].isdigit() and not e.msg[5].isdigit():
                    e.window.write("* %s %s %s" % (e.msg[3], e.msg[5], e.msg[4]))
                else:
                    e.window.write("* %s" % ' '.join(e.msg[3:]))
            
            else:
                e.window.write("* %s" % ' '.join(e.msg[3:]))
        elif e.msg[1] == 'ERROR':
            e.window.write("Error: %s" % e.text)

def onDisconnect(e):
    to_write = '%s* Disconnected' % prefix(e)
    if e.error:
        to_write += ' (%s)' % e.error

    for window in windows.get_with(network=e.network):
        if isinstance(window, windows.StatusWindow):
            window.write(to_write, widgets.TEXT)
        else:
            window.write(to_write, widgets.EVENT)
