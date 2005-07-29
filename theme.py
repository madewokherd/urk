import pango
import gtk

import ui

oldWindowInit = ui.IrcWindow.__init__

def newWindowInit(self, title=""):
    oldWindowInit(self, title)
    
    chatview_bg = gtk.gdk.color_parse("#2E3D49")
    chatview_fg = gtk.gdk.color_parse("#DEDEDE")
    chatview_font = pango.FontDescription("verdana 8")

    self.view.modify_text(gtk.STATE_NORMAL, chatview_fg)
    self.view.modify_base(gtk.STATE_NORMAL, chatview_bg)
    self.view.modify_font(chatview_font)
    
ui.IrcWindow.__init__ = newWindowInit

def preText(event):
    event.done = True

    if event.network.me == event.source:
        to_write = "\x02\x04FF00FF<\x04\x02%s\x02\x04FF00FF>\x04\x02 %s" % (event.source, event.text)
    else:
        to_write = "\x02\x040000CC<\x04\x02%s\x02\x040000CC>\x04\x02 %s" % (event.source, event.text)
        
    event.window.write(to_write)
    
def preJoin(event):
    event.done = True
    
    if event.network.me == event.source:
        to_write = "\x02You\x02 joined %s" % event.target
    else:
        to_write = "\x02%s\x02 (%s) joined %s" % (event.source, event.source.address, event.target)
        
    event.window.write(to_write)
        
def postRaw(event):
    if not event.done:
        event.window.write("* %s %s" % (event.source, event.text))
