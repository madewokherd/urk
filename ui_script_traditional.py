import ui
import chaninfo

# FIXME: meh still might want rid of these, I'm not sure yet

def onActive(window):
    window.activity = 0
        
    if window.role != ui.StatusWindow:
        title = "%s - %s - %s" % (window.network.me, window.network.server, window.title)
    else:
        title = "%s - %s" % (window.network.me, window.title)
    
    ui.set_title("%s - urk" % title)
    
    ui.register_idle(window.focus)

def onNick(e):
    if e.source == e.network.me:
        for w in ui.get_window_for(network=e.network):
            w.nick_label.update(e.newnick)     

def onExit(e):
    for w in ui.get_window_for(role=ui.StatusWindow):
        w.close()
        
# /FIXME


def get_status_window(network):
    # There can be only one...
    for window in ui.get_window_for(role=ui.StatusWindow, network=network):
        return window

ui.get_default_window = get_status_window

def preJoin(e):
    if e.source == e.network.me:
        ui.windows.new(ui.ChannelWindow, e.network, e.target).activate()
        
    e.window = ui.windows.get(ui.ChannelWindow, e.network, e.target) or e.window

def preText(e):
    if e.target == e.network.me:
        e.window = ui.windows.new(ui.QueryWindow, e.network, e.source)
    else:
        e.window = \
            ui.windows.get(ui.ChannelWindow, e.network, e.target) or \
            ui.windows.get(ui.QueryWindow, e.network, e.source) or \
            e.window

preAction = preText

def preOwnText(e):
    e.window = \
        ui.windows.get(ui.ChannelWindow, e.network, e.target) or \
        ui.windows.get(ui.QueryWindow, e.network, e.target) or \
        e.window

preOwnAction = preOwnText

def postPart(e):
    if e.source == e.network.me:
        window = ui.windows.get(ui.ChannelWindow, e.network, e.target)
        if window:
            window.close()

def onClose(window):
    if window.role == ui.ChannelWindow and \
            chaninfo.ison(window.network, window.id):
        window.network.part(window.id)
    elif window.role == ui.StatusWindow:
        if window.network.status:
            window.network.quit()
        
        for w in ui.get_window_for(network=window.network):
            if w is not window:
                w.close()   

def onConnect(e):
    window = ui.get_default_window(e.network)
    if window:
        window.title.update()

def onDisconnect(e):
    window = ui.get_default_window(e.network)
    if window:
        window.title.update()

def setupPart(e):
    e.window = ui.windows.get(ui.ChannelWindow, e.network, e.target) or e.window

setupTopic = setupPart

def setupKick(e):
    e.window = ui.windows.get(ui.ChannelWindow, e.network, e.channel) or e.window

def setupMode(e):
    if e.target != e.network.me:
        e.window = ui.windows.get(ui.ChannelWindow, e.network, e.target) or e.window
