import ui

def onActive(window):
    window.activity = 0
        
    if type(window) != ui.StatusWindow:
        title = "%s - %s - %s" % (window.network.me, window.network.server, window.title)
    else:
        title = "%s - %s" % (window.network.me, window.title)
    
    ui.set_title("%s - urk" % title)
    
    ui.register_idle(window.focus)

def onNick(event):
    if event.source == event.network.me:
        for w in ui.get_window_for(network=event.network):
            w.nick_label.update(event.newnick)     

def onExit(event):
    for n in set(w.network for w in ui.windows if w.network.status):
        n.quit()
