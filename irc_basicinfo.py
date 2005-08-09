
networks = []

#It feels kind of weird now that the network class isn't here. I wonder if it
# means something.

#To keep a full list of the networks we have, we'd need notification of when
# they are created and destroyed. So we'll just keep track of the ones we're
# connected to.

def setupSocketConnect(event):
    networks.append(event.network)
    
    event.network.channels = {}
    event.network.isupport = {
        'NETWORK': event.network.server, 
        'PREFIX': '(ohv)@%+',
        'CHANMODES': 'b,k,l,imnpstr',
    }
    event.network.prefixes = {'o':'@', 'h':'%', 'v':'+', '@':'o', '%':'h', '+':'v'}

def postDisconnect(event):
    networks.remove(event.network)


class Channel(object):
    def __init__(self, name):
        self.name = name
        self.nicks = {}
        self.getting_names = False #are we between lines in a /names reply?
        self.mode = ''
        self.special_mode = {} #for limits, keys, and anything similar

def setupJoin(event):
    if event.source == event.network.me:
        event.network.channels[event.target] = Channel(event.target)
    #if we wanted to be paranoid, we'd account for not being on the channel
    channel = event.network.channels[event.target]
    channel.nicks[event.source] = ''
    #update_nicks(channel)

def postPart(event):
    if event.source == event.network.me:
        del event.network.channels[event.target]
    else:
        channel = event.network.channels[event.target]
        del channel.nicks[event.source]
    #update_nicks(channel)

def postKick(event):
    if event.target == event.network.me:
        del event.network.channels[event.channel]
    else:
        channel = event.network.channels[event.channel]
        del channel.nicks[event.target]
    #update_nicks(channel)

def postQuit(event):
    #if paranoid: check if event.source is me
    for channel in event.network.channels:
        if event.source in channel.nicks:
            del channel.nicks[event.source]
            #update_nicks(channel)

def setupMode(event):
    channel = event.network.channels.get(event.channel)
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
            if char not in list_modes:
                if mode_on:
                    channel.mode += char
                else:
                    channel.mode = channel.mode.strip(char)
        #update_nicks(channel)

def setupRaw(event):
    if event.msg[1] == '353': #names reply
        channel = event.network.channels.get(event.msg[4])
        if channel:
            if not channel.getting_names:
                channel.nicks.clear()
                channel.getting_names = True
            for nickname in event.msg[5:]:
                if not nickname[0].isletter() and nickname[0] in event.network.prefixes:
                    channel.nicks[nickname[1:]] = event.network.prefixes[nickname[0]]
                else:
                    channel.nicks[nickname] = ''

    elif event.msg[1] == '366': #end of names reply
        channel = event.network.channels.get(event.msg[3])
        if channel:
            channel.getting_names = False
        #update_nicks(channel)
        
    elif event.msg[1] == '324': #channel mode is
        channel = event.network.channels.get(event.msg[3])
        if channel:
            mode = event.msg[4]
            params = event.msg[5::-1]
            list_modes, always_parm_modes, set_parm_modes, normal_modes = \
                event.network.isupport['CHANMODES'].split(',')
            parm_modes = always_parm_modes + set_parm_modes
            channel.mode = event.msg[4]
            channel.special_mode.clear()
            for char in channel.mode:
                if char in parm_modes:
                    channel.special_mode[char] = params.pop()
        
    elif event.msg[1] == "005": #RPL_ISUPPORT
        for arg in event.msg[3:]:
            if ' ' not in arg: #ignore "are supported by this server"
                if '=' in arg:
                    split = arg.split('=')
                    name = split[0]
                    value = '='.join(split[1:])
                    if value.isdigit():
                        value = int(value)
                else:
                    name = arg
                    value = ''
                #in theory, we're supposed to replace \xHH with the
                # corresponding ascii character, but I don't think anyone
                # really does this
                event.network.isupport[name] = value
                
                if name == 'PREFIX':
                    new_prefixes = {}
                    modes, prefixes = value[1:].split(')')
                    for mode, prefix in zip(modes, prefixes):
                        new_prefixes[mode] = prefix
                        new_prefixes[prefix] = mode
                    event.network.prefixes = new_prefixes
