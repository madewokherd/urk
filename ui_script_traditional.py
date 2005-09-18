import ui

def onActive(window):
    window.activity = 0
        
    if type(window) != ui.StatusWindow:
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
    for w in ui.get_window_for(type=ui.StatusWindow):
        w.close()
        

def preJoin(event):
    if event.source == event.network.me:
        ui.windows.new(ui.ChannelWindow, event.network, event.target).activate()
        
    event.window = ui.windows.get(ui.ChannelWindow, event.network, event.target) or event.window

def preText(event):
    if event.target == event.network.me:
        ui.windows.new(ui.QueryWindow, event.network, event.source)
    else:
        event.window = \
            ui.windows.get(ui.ChannelWindow, event.network, event.target) or \
            ui.windows.get(ui.QueryWindow, event.network, event.source) or \
            event.window

preAction = preText

def preOwnText(event):
    event.window = \
        ui.windows.get(ui.ChannelWindow, event.network, event.target) or \
        ui.windows.get(ui.QueryWindow, event.network, event.target) or \
        event.window

preOwnAction = preOwnText

def postPart(event):
    if event.source == event.network.me:
        window = ui.windows.get(ui.ChannelWindow, event.network, event.target)
        if window:
            window.close()

def onClose(window):
    if type(window) == ui.ChannelWindow and window.id in window.network.channels:
        window.network.part(window.id)
    elif type(window) == ui.StatusWindow:
        if window.network.status:
            window.network.quit()
        
        for w in ui.get_window_for(network=window.network):
            if w is not window:
                w.close()   

def onConnect(event):
    window = ui.get_default_window(event.network)
    if window:
        window.title.update()

def onDisconnect(event):
    window = ui.get_default_window(event.network)
    if window:
        window.title.update()

def setupPart(event):
    event.window = ui.windows.get(ui.ChannelWindow, event.network, event.target) or event.window

setupTopic = setupPart

def setupKick(event):
    event.window = ui.windows.get(ui.ChannelWindow, event.network, event.channel) or event.window

def setupMode(event):
    if event.target != event.network.me:
        event.window = ui.windows.get(ui.ChannelWindow, event.network, event.target) or event.window
