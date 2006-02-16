import events
import ui
import windows

def prefix(network, channel, nick):
    fr, to = network.isupport["PREFIX"][1:].split(")")

    for mode, prefix in zip(fr, to):
        if mode in channel.nicks[nick]:
            return prefix+nick
    return nick

def sort_key(network, channel, nick):
    fr, to = network.isupport["PREFIX"][1:].split(")")
    if nick[0] in to:
        nick = nick[1:]
    
    modes = channel.nicks[nick]
    
    return [mode not in modes for mode in fr] + [network.norm_case(nick)]

def nicklist_add(network, channel, nick):
    p = prefix(network, channel, nick)
    k = sort_key(network, channel, nick)
    
    window = windows.get(windows.ChannelWindow, network, channel.name)
    if window:
        lower_limit , upper_limit = 0, len(window.nicklist)
        while lower_limit < upper_limit:
            midpoint = (lower_limit+upper_limit)/2
            if sort_key(network, channel, window.nicklist[midpoint]) < k:
                lower_limit = midpoint+1
            else:
                upper_limit = midpoint
        window.nicklist.insert(lower_limit, p)

def nicklist_del(network, channel, nick):
    p = prefix(network, channel, nick)
    
    window = windows.get(windows.ChannelWindow, network, channel.name)
    if window:
        window.nicklist.remove(p)

def setupListRightClick(e):
    if isinstance(e.window, windows.ChannelWindow):
        if e.data[0] in e.window.network.isupport["PREFIX"].split(")")[1]:
            e.nick = e.data[1:]
        else:
            e.nick = e.data

def setupSocketConnect(e):
    e.network.channels = {}

def postDisconnect(e):
    e.network.channels = {}

class Channel(object):
    def __init__(self, name):
        self.name = name
        self.nicks = {}
        self.normal_nicks = {} # mapping of normal nicks to actual nicks
        self.getting_names = False #are we between lines in a /names reply?
        self.mode = ''
        self.special_mode = {} #for limits, keys, and anything similar
        self.topic = ''
        self.got_mode = False   #did we get at least one mode reply?
        self.got_names = False  #did we get at least one names reply?

def getchan(network, channel):
    return hasattr(network, 'channels') and network.channels.get(network.norm_case(channel))

#return a list of channels you're on on the given network
def channels(network):
    if hasattr(network,'channels'):
        return list(network.channels)
    else:
        network.channels = result = {}
        return result

#return True if you're on the channel
def ischan(network, channel):
    return channel in network.channels

#return True if the nick is on the channel
def ison(network, channel, nickname):
    channel = getchan(network, channel)
    return channel and network.norm_case(nickname) in channel.normal_nicks

#return a list of nicks on the given channel
def nicks(network, channel):
    channel = getchan(network, channel)
    return (channel or []) and list(channel.nicks)

#return the mode on the given channel
def mode(network, channel, nickname=''):
    channel = getchan(network, channel)
    if nickname:
        return channel.nicks[channel.normal_nicks[network.norm_case(nickname)]] \
                or ''
    result = channel.mode
    for m in channel.mode:
        if m in channel.special_mode:
            result += ' '+channel.special_mode[m]
    return result

#return the topic on the given channel
def topic(network, channel):
    channel = getchan(network, channel)
    return (channel or '') and channel.topic

def setupJoin(e):
    if e.source == e.network.me:
        e.network.channels[e.network.norm_case(e.target)] = Channel(e.target)
    #if we wanted to be paranoid, we'd account for not being on the channel
    channel = getchan(e.network,e.target)
    channel.nicks[e.source] = ''
    channel.normal_nicks[e.network.norm_case(e.source)] = e.source
    
    if e.source == e.network.me:
        #If the channel window already existed, and we're joining, then we 
        #didn't clear out the nicklist when we left. That means we have to clear
        #it out now.
        window = windows.get(windows.ChannelWindow, e.network, e.target)
        if window:
            window.nicklist.clear()
    nicklist_add(e.network, channel, e.source)

def onJoin(e):
    if e.source == e.network.me:
        e.network.raw('MODE '+e.target)

def postPart(e):
    if e.source == e.network.me:
        del e.network.channels[e.network.norm_case(e.target)]
    else:
        channel = getchan(e.network,e.target)
        nicklist_del(e.network, channel, e.source)
        del channel.nicks[e.source]
        del channel.normal_nicks[e.network.norm_case(e.source)]

def postKick(e):
    if e.target == e.network.me:
        del e.network.channels[e.network.norm_case(e.channel)]
    else:
        channel = getchan(e.network,e.channel)
        nicklist_del(e.network, channel, e.target)
        del channel.nicks[e.target]
        del channel.normal_nicks[e.network.norm_case(e.target)]

def postQuit(e):
    #if paranoid: check if e.source is me
    for channame in channels(e.network):
        channel = getchan(e.network,channame)
        if e.source in channel.nicks:
            nicklist_del(e.network, channel, e.source)
            del channel.nicks[e.source]
            del channel.normal_nicks[e.network.norm_case(e.source)]

def setupMode(e):
    channel = getchan(e.network,e.channel)
    if channel:
        mode_on = True #are we reading a + section or a - section?
        params = e.text.split(' ')[::-1]
        modes = params.pop()
        user_modes = e.network.isupport['PREFIX'].split(')')[0][1:]
        list_modes, always_parm_modes, set_parm_modes, normal_modes = \
            e.network.isupport['CHANMODES'].split(',')
        list_modes += user_modes
        for char in modes:
            if char == '+':
                mode_on = True
            elif char == '-':
                mode_on = False
            elif char in user_modes:
                #these are modes like op and voice
                nickname = params.pop()
                nicklist_del(e.network, channel, nickname)
                if mode_on:
                    channel.nicks[nickname] += char
                else:
                    channel.nicks[nickname] = channel.nicks[nickname].strip(char)
                nicklist_add(e.network, channel, nickname)
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

def postNick(e):
    for channame in channels(e.network):
        channel = getchan(e.network,channame)
        if e.source in channel.nicks:
            nicklist_del(e.network, channel, e.source)
            del channel.normal_nicks[e.network.norm_case(e.source)]
            channel.nicks[e.newnick] = channel.nicks[e.source]
            del channel.nicks[e.source]
            channel.normal_nicks[e.network.norm_case(e.newnick)] = e.newnick
            nicklist_add(e.network, channel, e.newnick)

def setupTopic(e):
    channel = getchan(e.network, e.target)
    if channel:
        channel.topic = e.text

def setupRaw(e):
    if e.msg[1] == '353': #names reply
        channel = getchan(e.network,e.msg[4])
        if channel:
            if not channel.getting_names:
                channel.nicks.clear()
                channel.normal_nicks.clear()
                channel.getting_names = True
            if not channel.got_names:
                e.quiet = True
            for nickname in e.msg[5].split(' '):
                if nickname:
                    if not nickname[0].isalpha() and nickname[0] in e.network.prefixes:
                        n = nickname[1:]
                        channel.nicks[n] = e.network.prefixes[nickname[0]]
                        channel.normal_nicks[e.network.norm_case(n)] = n
                    else:
                        channel.nicks[nickname] = ''
                        channel.normal_nicks[e.network.norm_case(nickname)] = nickname

    elif e.msg[1] == '366': #end of names reply
        channel = getchan(e.network,e.msg[3])
        if channel:
            if not channel.got_names:
                e.quiet = True
                channel.got_names = True
            channel.getting_names = False
            
            window = windows.get(windows.ChannelWindow, e.network, e.msg[3])
            if window:
                window.nicklist.clear()
                nicks = list(channel.nicks)
                def key(nick):
                    return sort_key(e.network, channel, nick)
                nicks.sort(key=key)
                window.nicklist.extend(prefix(e.network, channel, nick) for nick in nicks)
        
    elif e.msg[1] == '324': #channel mode is
        channel = getchan(e.network,e.msg[3])
        if channel:
            if not channel.got_mode:
                e.quiet = True
                channel.got_mode = True
            mode = e.msg[4]
            params = e.msg[:4:-1]
            list_modes, always_parm_modes, set_parm_modes, normal_modes = \
                e.network.isupport['CHANMODES'].split(',')
            parm_modes = always_parm_modes + set_parm_modes
            channel.mode = e.msg[4]
            channel.special_mode.clear()
            for char in channel.mode:
                if char in parm_modes:
                    channel.special_mode[char] = params.pop()
        
    elif e.msg[1] == '331': #no topic
        channel = getchan(e.network,e.msg[3])
        if channel:
            channel.topic = ''

    elif e.msg[1] == '332': #channel topic is
        channel = getchan(e.network,e.msg[3])
        if channel:
            channel.topic = e.text

events.load(__name__)
