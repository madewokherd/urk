import events
import ui

shortcuts = {
    '^b': '\x02',
    '^u': '\x1F',
    '^r': '\x16',
    '^k': '\x03',
    '^l': '\x04',
    '^o': '\x0F',
    }

def onKeypress(e):
    if e.key in shortcuts:
        e.window.input.insert(shortcuts[e.key])
    elif e.key == '^t':
        events.run_command('server -n',e.window,e.window.network)
    elif e.key == 'Tab' and type(e.window) == ui.ChannelWindow:
        i = e.window.input
        if not i.selection:
            text = i.text[:i.cursor]
            print repr(text)
