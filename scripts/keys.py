import ui

shortcuts = {
    '^b': '\x02',
    '^u': '\x1F',
    '^r': '\x16',
    '^k': '\x03',
    '^l': '\x04',
    '^o': '\x0F',
    }

def onKeyPressed(e):
    if e.key in shortcuts:
        e.window.input.insert(shortcuts[e.key])
        
    elif e.key == '!a':
        w = [w for w in ui.windows if w.activity > ui.EVENT]
        
        if w:
            ui.windows.manager.set_active(w[0])

    # tabbed browsing
    elif e.key == '^t':
        ui.windows.new(ui.StatusWindow, None, 'status').activate()

    elif e.key == '^w':
        ui.windows.manager.get_active().close()
    
    elif e.key == 'Page_Up':
        e.window.output.y = e.window.output.y - e.window.output.height / 2
    
    elif e.key == 'Page_Down':
        e.window.output.y = e.window.output.y + e.window.output.height / 2
