import ui
import windows

def handle_input(result, error):
    if result:
        windows.manager.get_active().entered_text(result)
    else:
        print(error)

    ui.fork(handle_input, raw_input)

ui.fork(handle_input, raw_input)

