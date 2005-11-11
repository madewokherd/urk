import ui
import chaninfo
import events

def channel_completer(window, left, right, text):
    network, input = window.network, window.input
    
    if text:
        insert_text = "%s%s%s" % (left[:-len(text)], "%s", right)
        cursor_pos = len(left[:-len(text)])
    else:
        insert_text = "%s%s%s" % (left, "%s", right)
        cursor_pos = len(left)

    candidates = [w.id for w in ui.windows.manager if w.role == ui.ChannelWindow]

    result = []       
    for channel in candidates:
        if channel.lower().startswith(text.lower()):
            result.append((insert_text % channel, cursor_pos + len(channel)))
                
    result.append((input.text, input.cursor))
            
    while True:
        for text, cursor in result:
            input.text, input.cursor = text, cursor
            yield None
            
# normal server commands
srv_commands = ['PING', 'JOIN', 'PART', 'MODE', 'SERVER', 'KICK',
                'QUIT', 'NICK', 'PRIVMSG', 'NOTICE', 'TOPIC']
            
def command_completer(window, left, right, text):
    network, input = window.network, window.input
    
    if text:
        insert_text = "%s%s%s" % (left[:-len(text)], "%s", right)
        cursor_pos = len(left[:-len(text)])
    else:
        insert_text = "%s%s%s" % (left, "%s", right)
        cursor_pos = len(left)

    candidates = [c.lower() for c in srv_commands]
    candidates += [e[7:].lower() for e in events.events if e.startswith('Command')]
    
    candidates = set('/%s' % c for c in candidates if c)

    result = []
    for command in candidates:
        if command.lower().startswith(text.lower()):
            result.append((insert_text % command, cursor_pos + len(command)))
                
    result.append((input.text, input.cursor))
            
    while True:
        for text, cursor in result:
            input.text, input.cursor = text, cursor
            yield None

def nick_completer(window, left, right, text):  
    network, input = window.network, window.input
 
    if left == text:
        suffix = ': '
    else:
        ' '
    
    if text:
        insert_text = "%s%s%s%s" % (left[:-len(text)], "%s", suffix, right)
        cursor_pos = len(left[:-len(text)] + suffix)
    else:
        insert_text = "%s%s%s%s" % (left, "%s", suffix, right)
        cursor_pos = len(left + suffix)

    candidates = list(recent_speakers.get(window, []))
    candidates += [n for n in chaninfo.nicks(network, window.id) if n not in candidates]
    
    candidates = [n for n in candidates if chaninfo.ison(network, window.id, n)]

    result = []       
    for nick in candidates:
        if nick.lower().startswith(text.lower()):
            result.append((insert_text % nick, cursor_pos + len(nick)))
                
    result.append((input.text, input.cursor))
            
    while True:
        for text, cursor in result:
            input.text, input.cursor = text, cursor
            yield None

def get_completer_for(window, text):
    if text and text[0] in window.network.isupport.get('CHANTYPES', '#&+'):
        return channel_completer
        
    elif text.startswith('/'):
        return command_completer
        
    else:
        return nick_completer
     
# generator--use recent_completer.next() to continue cycling through whatever
recent_completer = None

def onKeyPress(e):
    global recent_completer

    if e.key == 'Tab':
        if e.window.role == ui.ChannelWindow and \
            chaninfo.ischan(e.window.network, e.window.id):

            if not recent_completer:
                input = e.window.input
                
                left, right = input.text[:input.cursor], input.text[input.cursor:]
                
                text = left.split(' ')[-1]
                
                recent_completer = get_completer_for(e.window, text)(e.window, left, right, text)

            recent_completer.next()
    
    else:
        recent_completer = None

def onActive(window):
    global recent_completer
    
    recent_completer = None
    
#keep track of who recently spoke on each channel
recent_speakers = {}

def onText(e):
    if chaninfo.ischan(e.network, e.target):
        if e.window not in recent_speakers:
            recent_speakers[e.window] = []

        for nick in recent_speakers[e.window]:
            if nick == e.source or not chaninfo.ison(e.network, e.target, nick):
                recent_speakers[e.window].remove(nick)

        recent_speakers[e.window].insert(0, e.source)
onAction = onText

def onClose(window):
    if window in recent_speakers:
        del recent_speakers[window]
