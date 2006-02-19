import gtk

import urk
import windows
import ui

ui.gtk

try:
    import egg.trayicon
except:
    pass

class urktray:
    def __init__(self):
        self.tray = None
        self.tip = None
        self.urgent_window = None

    def clicked(self, widget, event):
        windows.manager.set_active(self.urgent_window)
        try:
            # since gtk 2.8...
            windows.manager.present_with_time(event.time)
        except:
            windows.manager.present()

    def window_hilighted(self, window, source):
        # if we are looking at the window already do not show the tray...
        if windows.manager.is_active():
            return

        if not self.tray:
            image = gtk.Image()
            (w, h) = gtk.icon_size_lookup(gtk.ICON_SIZE_SMALL_TOOLBAR)
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(urk.path("urk_icon.svg"), w, h)
            image.set_from_pixbuf(pixbuf)
            evbox = gtk.EventBox()
            evbox.set_visible_window(False)
            evbox.connect('button-press-event', self.clicked)
            evbox.add(image)
            self.tray = egg.trayicon.TrayIcon("Urk")
            self.tray.add(evbox)
            self.tip = gtk.Tooltips()

        self.tip.set_tip (self.tray, "%s (%s)" % (source, window.get_title()))
        self.urgent_window = window
        self.tray.show_all()

    def window_activated(self, window):
        if window == self.urgent_window:
            self.urgent_window = None
            self.tray.hide()

    def remove(self):
        if self.tray:
            self.tray.destroy()
            self.tray = None
            self.tip = None
        self.urgent_window = None



tray = urktray()

def postHilight(e):
    if e.hilight:
        tray.window_hilighted(e.window, e.source)

def onActive(window):
    tray.window_activated(window)
    
onSuperActive = onActive

def onClose(window):
    tray.remove()
