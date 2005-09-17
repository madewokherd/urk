import ui

def onNick(event):
    if event.source == event.network.me:
        for w in ui.get_window_for(network=event.network):
            w.nick_label.update(event.newnick)     

def onExit(event):
    for n in set(w.network for w in ui.windows if w.network.status):
        n.quit()
