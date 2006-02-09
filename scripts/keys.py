import ui

shortcuts = {
    '^b': '\x02',
    '^u': '\x1F',
    '^r': '\x16',
    '^k': '\x03',
    '^l': '\x04',
    '^o': '\x0F',
    }

def onKeyPress(e):
    if e.key in shortcuts:
        e.window.input.insert(shortcuts[e.key])

    elif e.key == 'Page_Up':
        e.window.output.y = e.window.output.y - e.window.output.height / 2
    
    elif e.key == 'Page_Down':
        e.window.output.y = e.window.output.y + e.window.output.height / 2

    elif e.key in ('^Page_Up', '^Page_Down'):
        windows = list(ui.windows.manager)
        index = windows.index(e.window) + ((e.key == '^Page_Down') and 1 or -1)
        if 0 <= index < len(windows):
	    windows[index].activate()

    elif e.key == '!a':
        windows = list(ui.windows.manager)
        windows = windows[windows.index(e.window):]+windows
        w = [w for w in windows if w.activity >= ui.HILIT]
        
        if not w:
            w = [w for w in windows if w.activity >= ui.TEXT]
        
        if w:
            ui.windows.manager.set_active(w[0])

    # tabbed browsing
    elif e.key == '^t':
        ui.windows.new(ui.StatusWindow, None, 'status').activate()

    elif e.key == '^w':
        ui.windows.manager.get_active().close()
        
    elif e.key == '^f':
        window = ui.windows.manager.get_active()
        
        find = ui.widgets.FindBox(window)
        
        window.pack_start(find, expand=False)
        
        find.textbox.grab_focus()
