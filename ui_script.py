import ui
import chaninfo

# FIXME: meh still might want rid of these, I'm not sure yet

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
        
# /FIXME
        

def preJoin(e):
    if e.source == e.network.me:
        status_window = ui.windows.get(ui.StatusWindow, e.network, 'status')
        
        if status_window:
            status_window.mutate(
                ui.ChannelWindow, (e.network, e.target)
                ).activate()
            
        else:
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
            cwindows = list(ui.get_window_for(
                            network=window.network,
                            type=ui.ChannelWindow
                            ))
                            
            if len(cwindows) == 1:
                window.mutate(
                    ui.StatusWindow, (e.network, 'status')
                    )
            else:
                window.close()

def onClose(window):
    if type(window) == ui.ChannelWindow: 
        if chaninfo.ischan(window.network, window.id):
            window.network.part(window.id) 
    
        cwindows = list(ui.get_window_for(
                            network=window.network,
                            type=ui.ChannelWindow
                            ))
        
        if len(cwindows) == 1:
            window.mutate(
                ui.StatusWindow, (e.network, 'status')
                )
        
    elif type(window) == ui.StatusWindow:
        window.network.quit()

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
