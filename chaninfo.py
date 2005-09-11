import events

# FIXME:
def update_nicks(network, channel):
    import ui
    
    # this sucks
    fr, to = network.isupport["PREFIX"].split(")")
    fr = fr[1:]

    def prefix(nick, pre=""):
        modes = channel.nicks[nick]
        
        for pos, mode in enumerate(fr):
            if mode in modes:
                pre = to[pos]
                break

        return "%s%s" % (pre, nick)
    
    def status(nick):
        modes = channel.nicks[nick]

        return [mode not in modes for mode in fr] + [nick.lower()]

    nicklist = [prefix(nick) for nick in sorted(channel.nicks, key=status)]
    
    for window in ui.get_window_for(network=network, type="channel", id=channel.name):
        window.set_nicklist(nicklist)

def setupSocketConnect(event):
    event.network.channels = {}

def postDisconnect(event):
    event.network.channels = {}

class Channel(object):
    def __init__(self, name):
        self.name = name
        self.nicks = {}
        self.getting_names = False #are we between lines in a /names reply?
        self.mode = ''
        self.special_mode = {} #for limits, keys, and anything similar
        self.topic = ''

def setupJoin(event):
    if event.source == event.network.me:
        event.network.channels[event.network.normalize_case(event.target)] = Channel(event.target)
    #if we wanted to be paranoid, we'd account for not being on the channel
    channel = event.network.channels[event.network.normalize_case(event.target)]
    channel.nicks[event.source] = ''
    
    update_nicks(event.network, channel)

def onJoin(event):
    if event.source == event.network.me:
        event.network.raw('MODE '+event.target)

def postPart(event):
    if event.source == event.network.me:
        del event.network.channels[event.network.normalize_case(event.target)]
    else:
        channel = event.network.channels[event.network.normalize_case(event.target)]
        del channel.nicks[event.source]
        
        update_nicks(event.network, channel)

def postKick(event):
    if event.target == event.network.me:
        del event.network.channels[event.network.normalize_case(event.channel)]
    else:
        channel = event.network.channels[event.network.normalize_case(event.channel)]
        del channel.nicks[event.target]
        
        update_nicks(event.network, channel)

def postQuit(event):
    #if paranoid: check if event.source is me
    for channame in event.network.channels:
        channel = event.network.channels[channame]
        if event.source in channel.nicks:
            del channel.nicks[event.source]
            
            update_nicks(event.network, channel)

def setupMode(event):
    channel = event.network.channels.get(event.network.normalize_case(event.channel))
    if channel:
        mode_on = True #are we reading a + section or a - section?
        params = event.text.split(' ')[::-1]
        modes = params.pop()
        user_modes = event.network.isupport['PREFIX'].split(')')[0][1:]
        list_modes, always_parm_modes, set_parm_modes, normal_modes = \
            event.network.isupport['CHANMODES'].split(',')
        list_modes += user_modes
        for char in modes:
            if char == '+':
                mode_on = True
            elif char == '-':
                mode_on = False
            elif char in user_modes:
                #these are modes like op and voice
                nickname = params.pop()
                if mode_on:
                    channel.nicks[nickname] += char
                else:
                    channel.nicks[nickname] = channel.nicks[nickname].strip(char)
            elif char in always_parm_modes:
                #these always have a parameter
                if mode_on:
                    channel.special_mode[char] = params.pop()
                else:
                    del channel.special_mode[char]
                    params.pop()
            elif char in set_parm_modes:
                #these have a parameter if they're being set
                if mode_on:
                    channel.special_mode[char] = params.pop()
                else:
                    del channel.special_mode[char]
            if char not in list_modes and char not in '+-':
                if mode_on:
                    channel.mode = channel.mode.strip(char)+char
                else:
                    channel.mode = channel.mode.strip(char)

        update_nicks(event.network, channel)

def postNick(event):
    for channame in event.network.channels:
        channel = event.network.channels[channame]
        if event.source in channel.nicks:
            channel.nicks[event.newnick] = channel.nicks[event.source]
            del channel.nicks[event.source]

        update_nicks(event.network, channel)

def setupTopic(event):
    if event.network.normalize_case(event.target) in event.network.channels:
        channel = event.network.channels[event.network.normalize_case(event.target)]
        channel.topic = event.text

def setupRaw(event):
    if event.msg[1] == '353': #names reply
        channel = event.network.channels.get(event.network.normalize_case(event.msg[4]))
        if channel:
            if not channel.getting_names:
                channel.nicks.clear()
                channel.getting_names = True
            for nickname in event.msg[5].split(' '):
                if nickname:
                    if not nickname[0].isalpha() and nickname[0] in event.network.prefixes:
                        channel.nicks[nickname[1:]] = event.network.prefixes[nickname[0]]
                    else:
                        channel.nicks[nickname] = ''

    elif event.msg[1] == '366': #end of names reply
        channel = event.network.channels.get(event.network.normalize_case(event.msg[3]))
        if channel:
            channel.getting_names = False
 
            update_nicks(event.network, channel)
        
    elif event.msg[1] == '324': #channel mode is
        channel = event.network.channels.get(event.network.normalize_case(event.msg[3]))
        if channel:
            mode = event.msg[4]
            params = event.msg[:4:-1]
            list_modes, always_parm_modes, set_parm_modes, normal_modes = \
                event.network.isupport['CHANMODES'].split(',')
            parm_modes = always_parm_modes + set_parm_modes
            channel.mode = event.msg[4]
            channel.special_mode.clear()
            for char in channel.mode:
                if char in parm_modes:
                    channel.special_mode[char] = params.pop()
        
    elif event.msg[1] == '331': #no topic
        channel = event.network.channels.get(event.network.normalize_case(event.msg[3]))
        if channel:
            channel.topic = ''

    elif event.msg[1] == '332': #channel topic is
        channel = event.network.channels.get(event.network.normalize_case(event.msg[3]))
        if channel:
            channel.topic = event.text

events.load('irc_events_us')
