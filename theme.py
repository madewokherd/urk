import pango
import gtk

import ui

#FIXME: ui should implement a "nice" interface to this
# Also, the effect go away when we unload
oldWindowInit = ui.IrcWindow.__init__

def newWindowInit(self, *args, **kwargs):
    oldWindowInit(self, *args, **kwargs)
    
    chatview_bg = gtk.gdk.color_parse("#2E3D49")
    chatview_fg = gtk.gdk.color_parse("#DEDEDE")
    chatview_font = pango.FontDescription("sans 8")

    self.view.modify_text(gtk.STATE_NORMAL, chatview_fg)
    self.view.modify_base(gtk.STATE_NORMAL, chatview_bg)
    self.view.modify_font(chatview_font)
    
ui.IrcWindow.__init__ = newWindowInit

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
    if event.network.me == event.network.normalize_case(event.source):
        color = '\x02\x04FF00FF'
    else:
        color = '\x02\x040000CC'
    to_write = "%s*\x0F %s %s" % (color, event.source, event.text)
    
    if not event.quiet:
        event.window.write(to_write, ui.TEXT)
    
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
    for network, type, id in ui.window_list:
        if network == event.network:
            ui.window_list[network, type, id].write('* Disconnected')
