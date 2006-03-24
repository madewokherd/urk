import windows
import chaninfo
import events
from conf import conf

def channel_completer(window, left, right, text):
    return [w.id for w in windows.get_with(wclass=windows.ChannelWindow)]
            
# normal server commands
srv_commands = ['PING', 'JOIN', 'PART', 'MODE', 'SERVER', 'KICK',
                'QUIT', 'NICK', 'PRIVMSG', 'NOTICE', 'TOPIC']
            
def command_completer(window, left, right, text):
    candidates = [c.lower() for c in srv_commands]
    candidates += [e[7:].lower() for e in events.events if e.startswith('Command')]

    return set('/%s' % c for c in candidates if c)

def nick_completer(window, left, right, text):  
    network = window.network

    candidates = list(getattr(window, 'recent_speakers', []))
    candidates += [n for n in chaninfo.nicks(network, window.id) if n not in candidates]

    return [n for n in candidates if chaninfo.ison(network, window.id, n)]
    
def script_completer(window, left, right, text):
    return list(events.loaded)
    
def network_completer(window, left, right, text):
    return list(conf.get('networks', ()))

def get_completer_for(window, left, right, text, fulltext):
    if text and text[0] in window.network.isupport.get('CHANTYPES', '#&+'):
        candidates = channel_completer(window, left, right, text)
        suffix = ''
        
    elif fulltext.startswith('/reload '):
        candidates = script_completer(window, left, right, text)
        suffix = ''
    
    elif fulltext.startswith('/edit '):
        candidates = script_completer(window, left, right, text)
        suffix = ''
        
    elif fulltext.startswith('/server '):
        candidates = network_completer(window, left, right, text)
        suffix = ''
        
    elif text.startswith('/'):
        candidates = command_completer(window, left, right, text)
        suffix = ' '
        
    else:
        candidates = nick_completer(window, left, right, text)
        
        if left == text:
            suffix = ': '
        else:
            suffix = ' '
            
    if text:
        insert_text = "%s%s%s%s" % (left[:-len(text)], "%s", suffix, right)
        cursor_pos = len(left[:-len(text)] + suffix)
    else:
        insert_text = "%s%s%s%s" % (left, "%s", suffix, right)
        cursor_pos = len(left + suffix)
        
    result = []       
    for res in candidates:
        if res.lower().startswith(text.lower()):
            result += [(insert_text % res, cursor_pos + len(res))]
                
    result += [(window.input.text, window.input.cursor)]
            
    while True:
        for text, cursor in result:
            window.input.text, window.input.cursor = text, cursor
            yield None
     
# generator--use recent_completer.next() to continue cycling through whatever
recent_completer = None

def onKeyPress(e):
    global recent_completer, recent_text

    if e.key == 'Tab':
        if not recent_completer:
            input = e.window.input
            
            left, right = input.text[:input.cursor], input.text[input.cursor:]
            
            text = left.split(' ')[-1]
            
            recent_completer = get_completer_for(e.window, left, right, text, input.text)

        recent_completer.next()
    
    else:
        recent_completer = None

def onActive(window):
    global recent_completer
    
    recent_completer = None

def onText(e):
    if chaninfo.ischan(e.network, e.target):
        if not hasattr(e.window, 'recent_speakers'):
            e.window.recent_speakers = []

        for nick in e.window.recent_speakers:
            if nick == e.source or not chaninfo.ison(e.network, e.target, nick):
                e.window.recent_speakers.remove(nick)

        e.window.recent_speakers.insert(0, e.source)

onAction = onText
