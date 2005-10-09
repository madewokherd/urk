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
  
def completer(window):
    network = window.network
    i = window.input

    left, right = i.text[:i.cursor], i.text[i.cursor:]
            
    text = left.split(' ')[-1]
    
    suffix = (left==text) and ': ' or ' '
    
    insert_text = "%s%s%s%s" % (left[:-len(text)], "%s", suffix, right)
    cursor_pos = len(left[:-len(text)] + suffix)

    candidates = recent_speakers[network][window.id] + \
                    chaninfo.nicks(network, window.id)

    result = []       
    for nick in candidates:
        if network.norm_case(nick).startswith(network.norm_case(text))\
                and nick not in result and chaninfo.ison(network, window.id, nick):
            result.append((insert_text % nick, cursor_pos + len(nick)))
                
    result.append((i.text, i.cursor))
            
    while True:
        for text, cursor in result:
            i.text, i.cursor = text, cursor
            yield None
            
#generator--use recent_completer.next() to continue cycling through nicks
recent_completer = None

def onKeypress(e):
    global recent_completer

    if e.key in shortcuts:
        e.window.input.insert(shortcuts[e.key])
    elif e.key == '^t':
        events.run_command('server -n',e.window,e.window.network)
    elif e.key == 'Tab' and e.window.role == ui.ChannelWindow and \
            chaninfo.ischan(e.window.network, e.window.id):

        if not recent_completer:
            recent_completer = completer(e.window)

        recent_completer.next()
            
    if e.key != 'Tab':
        recent_completer = None

def onActive(window):
    global recent_completer
    
    recent_completer = None

#keep track of who recently spoke on each channel
if "recent_speakers" not in globals():
    recent_speakers = {}
def onSocketConnect(e):
    recent_speakers[e.network] = {}
def onDisconnect(e):
    if e.network in recent_speakers:
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
    if chaninfo.ischan(e.network, e.target):
        channel = e.network.norm_case(e.target)
    
        if channel not in recent_speakers[e.network]:
            recent_speakers[e.network][channel] = []

        for nick in recent_speakers[e.network][channel]:
            if nick == e.source or not chaninfo.ison(e.network, e.target, nick):
                recent_speakers[e.network][channel].remove(nick)

        recent_speakers[e.network][channel].insert(0, e.source)
onAction = onText
