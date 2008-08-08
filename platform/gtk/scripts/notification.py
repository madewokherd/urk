import gtk

import urk
import windows
import ui

ui.gtk

try:
    from gtk import StatusIcon as TrayIcon
except:
    print "You need PyGtk 2.10 or above for the tray icon support."
    print "Tray icon support will be disabled, but you can still use urk normally."
    raise #still raise an exception so the script isn't loaded

class urktray:
    def __init__(self):
        self.tray = None
        self.urgent_window = None

    def clicked(self, widget):
        windows.manager.set_active(self.urgent_window)
        windows.manager.present()

    def window_hilighted(self, window, source):
        # if we are looking at the window already do not show the tray...
        if windows.manager.is_active():
            return

        if not self.tray:
            self.tray = TrayIcon()
            self.tray.set_from_file(urk.path("urk_icon.svg"))
            self.tray.connect('activate', self.clicked)

        self.tray.set_tooltip ("%s (%s)" % (source, window.get_title()))
        self.urgent_window = window
        self.tray.props.visible = True

    def window_activated(self, window):
        if window == self.urgent_window:
            self.urgent_window = None
            self.tray.props.visible = False

    def remove(self):
        if self.tray:
            self.tray.props.visible = False
            self.tray = None
        self.urgent_window = None


tray = urktray()

def setdownHighlight(e):
    if e.Highlight:
        tray.window_hilighted(e.window, e.source)

def onText(e):
    if isinstance(e.window, windows.QueryWindow):
        tray.window_hilighted(e.window, e.source)

def onActive(e):
    tray.window_activated(e.window)
    
onSuperActive = onActive

def onClose(e):
    tray.remove()
