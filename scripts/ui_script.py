import irc
import ui
import windows
import chaninfo

# FIXME: meh still might want rid of these, I'm not sure yet

def onActive(w):
    w.activity = 0

    ui.register_idle(windows.manager.set_title)

def onNick(e):
    if e.source == e.network.me:
        for w in windows.get_with(network=e.network):
            w.nick_label.update(e.newnick)     

def onExit(e):
    for n in set(w.network for w in windows.manager):
        n.quit()

def preJoin(e):
    if e.source == e.network.me:
        window = windows.get(windows.StatusWindow, e.network, 'status')
        
        if window:
            window.mutate(windows.ChannelWindow, e.network, e.target)
            window.focus()
            
        else:
            windows.new(windows.ChannelWindow, e.network, e.target).activate()

    e.window = windows.get(windows.ChannelWindow, e.network, e.target) or e.window

def preText(e):
    if e.target == e.network.me:
        e.window = windows.new(windows.QueryWindow, e.network, e.source)
    else:
        e.window = \
            windows.get(windows.ChannelWindow, e.network, e.target) or \
            windows.get(windows.QueryWindow, e.network, e.source) or \
            e.window

preAction = preText

def preNotice(e):
    if e.target != e.network.me:
        e.window = \
            windows.get(windows.ChannelWindow, e.network, e.target) or e.window

def preOwnText(e):
    e.window = \
        windows.get(windows.ChannelWindow, e.network, e.target) or \
        windows.get(windows.QueryWindow, e.network, e.target) or \
        e.window

preOwnAction = preOwnText

def postPart(e):
    if e.source == e.network.me:
        window = windows.get(windows.ChannelWindow, e.network, e.target)        
        
        if window:
            cwindows = list(windows.get_with(
                                network=window.network,
                                wclass=windows.ChannelWindow
                                ))
                            
            if len(cwindows) == 1:
                window.mutate(windows.StatusWindow, e.network, 'status')
                window.focus()
            else:
                window.close()

def onClose(window):
    if isinstance(window, windows.ChannelWindow): 
        cwindows = list(windows.get_with(
                            network=window.network,
                            wclass=windows.ChannelWindow
                            ))
        
        if len(cwindows) == 1:
            window.network.quit()
            
        elif chaninfo.ischan(window.network, window.id):
            window.network.part(window.id) 
        
    elif isinstance(window, windows.StatusWindow):
        window.network.quit()
        
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
