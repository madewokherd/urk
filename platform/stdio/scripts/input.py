import ui
import windows

def handle_input(result, error):
    if result is not None:
        windows.manager.get_active().entered_text(result)
    elif isinstance(error, EOFError):
        windows.manager.exit()
        return

    ui.fork(handle_input, raw_input)

ui.fork(handle_input, raw_input)

