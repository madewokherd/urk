import events
import ui
import windows
import chaninfo
from conf import conf

def set_target(e):
    target_l = e.target.lstrip('@+%.(<')
    e._target_fr = e.target_fr + len(e.target) - len(target_l)
    
    target_r = e.target.rstrip(')>:,')
    e._target_to = e.target_to - len(e.target) + len(target_r)
    
    e._target = e.text[e._target_fr:e._target_to]

def is_nick(e):
    return isinstance(e.window, windows.ChannelWindow) and \
            chaninfo.ison(e.window.network, e.window.id, e._target)
    
def is_url(e):
    def starts(prefix, mindots=1):
        def prefix_url(target):
            return target.startswith(prefix) and target.count('.') >= mindots
            
        return prefix_url
    
    to_check = [starts(*x) for x in [
        ('http://', 1),
        ('https://', 1),
        ('ftp://', 1),
        ('www', 2),
        ]]

    for check_url in to_check:
        if check_url(e._target):
            return True
    
    return False
    
def is_chan(e):
    # click on a #channel
    return e.window.network and e._target and \
            e._target[0] in e.window.network.isupport.get('CHANTYPES', '&#$+')

def get_autojoin_list(network):
    perform = conf.get('networks',{}).get(network.name,{}).get('perform',())
    channels = set()
    for line in perform:
        if line.startswith('join ') and ' ' not in line[5:]:
            channels.update(line[5:].split(','))
    return channels

def add_autojoin(network, channel):
    if 'networks' not in conf:
        conf['networks'] = {}
    if network.name not in conf['networks']:
        conf['networks'][network.name] = {'server': network.server}
        conf['start_networks'] = conf.get('start_networks',[]) + [network.name]
    if 'perform' in conf['networks'][network.name]:
        perform = conf['networks'][network.name]['perform']
    else:
        perform = conf['networks'][network.name]['perform'] = []
    
    for n, line in enumerate(perform):
        if line.startswith('join ') and ' ' not in line[5:]:
            perform[n] = "%s,%s" % (line, channel)
            break
    else:
        perform.append('join %s' % channel)

def make_nick_menu(e, target):
    def query():
        events.run('query %s' % target, e.window, e.window.network)
    
    def whois():
        events.run('whois %s' % target, e.window, e.window.network)
    
    e.menu += [
        ('Query', query),
        ('Whois', whois),
        (),
        ]

def onHover(e):
    set_target(e)

    for is_check in (is_nick, is_url, is_chan):
        if is_check(e):
            e.tolink.add((e._target_fr, e._target_to))
            break

def onClick(e):
    set_target(e)

    if is_nick(e):
        events.run('query %s' % e._target, e.window, e.window.network)
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif is_url(e):
        if e._target.startswith('www'):
            e._target = 'http://%s' % e._target
        ui.open_file(e._target)
    
    # click on a #channel
    elif is_chan(e):
        if not chaninfo.ischan(e.window.network, e._target):
            e.window.network.join(e._target)
        window = windows.get(windows.ChannelWindow, e.window.network, e._target)
        if window:
            window.activate()

def onRightClick(e):
    set_target(e)

    # nick on this channel
    if is_nick(e):
        make_nick_menu(e, e._target)

    elif is_url(e):
        if e._target.startswith('www'):
            e._target = 'http://%s' % e._target
    
        def copy_to():
            # copy to clipboard
            ui.set_clipboard(e._target)
            
        e.menu += [('Copy', copy_to)]
        
    elif is_chan(e):
        def add_to_perform():
            if 'networks' not in conf:
                conf['networks'] = {}
            networks = conf['networks']
            if e.window.network.name not in networks:
                networks[e.window.network.name] = {}
            
            network = networks[e.window.network.name]

            for i, command in enumerate(network.get('perform',())):
                # this might be worth updating to account for channel keys
                if command.lower().startswith('join ') and command.count(' ') == 1:
                    network['perform'][i] += ',%s' % e._target
                    break
            else:
                network['perform'] = network.get('perform',[])+('join %s' % e._target)
            
        def remove_from_perform():
            for network in conf.get('networks',{}):
                if network == e.window.network.name or \
                        conf['networks'][network][server] == e.window.network.server:
                    perform = conf['networks'][network]['perform']
                    for n, line in enumerate(perform):
                        if line.startswith('join ') and ' ' not in line[6:]:
                            channels = line[6:].split(',')
                            if e._target in channels:
                                channels.remove(e._target)
                                if channels:
                                    perform[n] = 'join %s' % ','.join(channels)
                                else:
                                    perform.pop(n)
                                    if not perform:
                                        conf['networks'].pop(network)
                                        if network in conf['start_networks']:
                                            conf['start_networks'].remove(network)
                                break
            # remove if it's already there maybe
            pass
            
        #e.menu.append(('Join channel automatically', add_to_perform))

def onListRightClick(e):
    make_nick_menu(e, e.nick)
