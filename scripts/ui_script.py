import irc
import ui
import windows
import chaninfo

# FIXME: meh still might want rid of these, I'm not sure yet

def onActive(e):
    e.window.activity = None

    ui.register_idle(windows.manager.set_title)

def setupNick(e):
    if e.source == e.network.me:
        for w in windows.get_with(network=e.network):
            try:
                w.nick_label.update(e.target)
            except AttributeError:
                pass    

def onExit(e):
    for n in set(w.network for w in windows.manager):
        if n:
            n.quit()

def setupJoin(e):
    if e.source == e.network.me:
        window = windows.get(windows.StatusWindow, e.network, 'status')
        
        if window:
            window.mutate(windows.ChannelWindow, e.network, e.target)
            window.activate()
            
        else:
            windows.new(windows.ChannelWindow, e.network, e.target).activate()

    e.window = windows.get(windows.ChannelWindow, e.network, e.target) or e.window

def setupText(e):
    if e.target == e.network.me:
        e.window = windows.new(windows.QueryWindow, e.network, e.source)
    else:
        e.window = \
            windows.get(windows.ChannelWindow, e.network, e.target) or \
            windows.get(windows.QueryWindow, e.network, e.source) or \
            e.window

setupAction = setupText

def setupNotice(e):
    if e.target != e.network.me:
        e.window = \
            windows.get(windows.ChannelWindow, e.network, e.target) or e.window

def setupOwnText(e):
    e.window = \
        windows.get(windows.ChannelWindow, e.network, e.target) or \
        windows.get(windows.QueryWindow, e.network, e.target) or \
        e.window

setupOwnAction = setupOwnText

def setdownPart(e):
    if e.source == e.network.me:
        window = windows.get(windows.ChannelWindow, e.network, e.target)        
        
        if window:
            cwindows = list(windows.get_with(
                                network=window.network,
                                wclass=windows.ChannelWindow
                                ))
                            
            if len(cwindows) == 1:
                window.mutate(windows.StatusWindow, e.network, 'status')
                window.activate()
            else:
                window.close()

def onClose(e):
    if isinstance(e.window, windows.ChannelWindow): 
        cwindows = list(windows.get_with(
                            network=e.window.network,
                            wclass=windows.ChannelWindow
                            ))
        
        if len(cwindows) == 1:
            e.window.network.quit()
            
        elif chaninfo.ischan(e.window.network, e.window.id):
            e.window.network.part(e.window.id) 
        
    elif isinstance(e.window, windows.StatusWindow):
        e.window.network.quit()
        
    if len(windows.manager) == 1:
        windows.new(windows.StatusWindow, irc.Network(), "status")

def onConnect(e):
    window = windows.get_default(e.network)
    if window:
        window.update()

onDisconnect = onConnect

def setupPart(e):
    e.window = windows.get(windows.ChannelWindow, e.network, e.target) or e.window

setupTopic = setupPart

def setupKick(e):
    e.window = windows.get(windows.ChannelWindow, e.network, e.channel) or e.window

def setupMode(e):
    if e.target != e.network.me:
        e.window = windows.get(windows.ChannelWindow, e.network, e.target) or e.window
