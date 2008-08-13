import ui
import windows

active_window = None

def handle_input(result, error):
    if result is not None:
        windows.manager.get_active().entered_text(result)
    elif isinstance(error, EOFError):
        windows.manager.exit()
        return

    ui.fork(handle_input, raw_input)

def onActive(e):
    global active_window
    if active_window != e.window.id:
        active_window = e.window.id
        print "Active window is now %s" % e.window.id

def onCommandW(e):
    if len(e.args) >= 1:
        for window in windows.manager:
            if window.id == e.args[0]:
                window.activate()
                break
    else:
        print "Active window is now %s" % windows.get_active().id

ui.fork(handle_input, raw_input)

