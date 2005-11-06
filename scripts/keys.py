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

    elif e.key == '^t':
        ui.windows.new(ui.StatusWindow, None, 'status').activate()
