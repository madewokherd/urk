import events
import ui
import chaninfo

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
    elif e.key == 'Tab' and e.window.role == ui.ChannelWindow and \
            chaninfo.ischan(e.window.network, e.window.id):
        i = e.window.input
        network = e.window.network
        if not i.selection:
            if recent_completion:
                result, left, text, right = recent_completion
            else:
                text = i.text[:i.cursor]
                if ' ' in text:
                    left, text = text.rsplit(' ', 1)
                    left += ' '
                else:
                    left = ''
                right = i.text[i.cursor:]
                candidates = recent_speakers[network][e.window.id] + \
                    chaninfo.nicks(network, e.window.id)
                result = []
                for nick in candidates:
                    if network.norm_case(nick).startswith(network.norm_case(text))\
                            and nick not in result and chaninfo.ison(network, e.window.id, nick):
                        result.append(nick)
            if result:
                suffix = left and ' ' or ': '
                i.text = left+result[0]+suffix+right
                i.cursor = len(left+result[0]+suffix)
                recent_completion[:] = result[1:], left, text, right
            else:
                i.text = left+text+right
                i.cursor = len(left+text)
                recent_completion[:] = []
    if e.key != 'Tab':
        recent_completion[:] = []

def onActive(window):
    recent_completion[:] = []

#the most list of possibilities, search string, text before search string, text after
recent_completion = []

#keep track of who recently spoke on each channel
if "recent_speakers" not in globals():
    recent_speakers = {}
def onSocketConnect(e):
    recent_speakers[e.network] = {}
def onDisconnect(e):
    del recent_speakers[e.network]

def onJoin(e):
    if e.source == e.network.me:
        recent_speakers[e.network][e.network.norm_case(e.target)] = []
def leftChan(network, channel):
    del recent_speakers[network][network.norm_case(channel)]

def onPart(e):
    if e.source == e.network.me:
        leftChan(e.network, e.target)
def onKick(e):
    if e.target == e.network.me:
        leftChan(e.network, e.channel)

def onText(e):
    nicklist = recent_speakers[e.network].get(e.network.norm_case(e.target))
    if nicklist is not None:
        nicklist[:] = [e.source] + [nick for nick in nicklist if nick != e.source and chaninfo.ison(e.network, e.target, nick)]
onAction = onText
