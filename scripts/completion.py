import windows
import chaninfo
import events
from conf import conf

def channel_completer(window, left, right, text):
    return (w.id for w in windows.get_with(wclass=windows.ChannelWindow))
            
# normal server commands
srv_commands = ('ping', 'join', 'part', 'mode', 'server', 'kick',
                'quit', 'nick', 'privmsg', 'notice', 'topic')
            
def command_completer(window, left, right, text):
    for c in srv_commands:
        yield '/%s' % c
        
    for c in events.events:
        if c.startswith('Command') and c != 'Command':
            yield '/%s' % [7:].lower()

def nick_completer(window, left, right, text):  
    recent_speakers = getattr(window, 'recent_speakers', ())
    
    for nick in recent_speakers:
        if chaninfo.ison(window.network, window.id, nick):
            yield nick

    for nick in chaninfo.nicks(window.network, window.id):
        if nick not in recent_speakers:
            yield nick
    
def script_completer(window, left, right, text):
    return events.loaded.iterkeys()
    
def network_completer(window, left, right, text):
    return conf.get('networks', {}).iterkeys()

def get_completer_for(window):
    input = window.input

    left, right = input.text[:input.cursor], input.text[input.cursor:]
            
    text = left.split(' ')[-1]
    fulltext = 

    suffix = ''

    if text and text[0] in window.network.isupport.get('CHANTYPES', '#&+'):
        candidates = channel_completer(window, left, right, text)
        
    elif input.text.startswith('/reload '):
        candidates = script_completer(window, left, right, text)
    
    elif input.text.startswith('/edit '):
        candidates = script_completer(window, left, right, text)
        
    elif input.text.startswith('/server '):
        candidates = network_completer(window, left, right, text)
        
    elif input.text.startswith('/'):
        candidates = command_completer(window, left, right, text)
        suffix = ' '
        
    else:
        candidates = nick_completer(window, left, right, text)
        
        if left == text:
            suffix = ': '
        else:
            suffix = ' '
            
    if text:
        before = left[:-len(text)]
    else:
        before = left
        
    insert_text = '%s%s%s%s' % (before, '%s', suffix, right)
    cursor_pos = len(before + suffix)

    original = window.input.text, window.input.cursor
            
    while True:
        for cand in candidates:
            if cand.lower().startswith(text.lower()):
                window.input.text, window.input.cursor = insert_text % res, cursor_pos + len(res)
                yield None
                
        window.input.text, window.input.cursor = original
     
# generator--use recent_completer.next() to continue cycling through whatever
recent_completer = None

def onKeyPress(e):
    global recent_completer

    if e.key == 'Tab':
        if not recent_completer:
            recent_completer = get_completer_for(e.window)

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
