import events
import ui
import chaninfo
from conf import conf

def is_nick(e, target):
    def query():
        events.run('query %s' % target, e.window, e.window.network)
    
    def whois():
        events.run('whois %s' % target, e.window, e.window.network)
    
    e.menu += [
        ("Query", query),
        ("Whois", whois),
        (),
        ]
    
def is_url(e, target):
    def copy_to():
        # copy to clipboard
        ui.set_clipboard(target)
        
    e.menu.append(('Copy', copy_to))
    
def is_chan(e, target):
    def add_to_perform():
        if 'networks' not in conf:
            conf['networks'] = {}
        networks = conf['networks']
        if e.window.network.name in networks:
            network = networks[e.window.network.name]
        else:
            network_name = e.window.network.isupport.get('NETWORK',e.network.server)
            while network_name in networks:
                network_name += '_'
            network = networks[network_name] = {}
        for i, command in enumerate(network.get('perform',())):
            # this might be worth updating to account for channel keys
            if command.lower().startswith('join ') and command.count(' ') == 1:
                network['perform'][i] += ','+target
                break
        else:
            network['perform'] = network.get('perform',[])+('join %s' % target)
        
    def remove_from_perform():
        # remove if it's already there maybe
        pass
        
    #e.menu.append(('Join channel automatically', add_to_perform))

def onRightClick(e):
    # nick on this channel
    target_l = e.target.lstrip('@+%.(<')
    target_fr = e.target_fr + len(e.target) - len(target_l)
    
    target_r = e.target.rstrip(')>:,')
    target_to = e.target_to - len(e.target) + len(target_r)
    
    target = e.text[target_fr:target_to]
    
    if e.window.role == ui.ChannelWindow and \
            chaninfo.ison(e.window.network, e.window.id, target):

        is_nick(e, target)

    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif (target.startswith("http://") and target.count(".") >= 1) or \
         (target.startswith("https://") and target.count(".") >= 1) or \
         (target.startswith("www") and target.count(".") >= 2):
        if target.startswith("www"):
            target = "http://"+target
        
        is_url(e, target)
    
    # click on a #channel
    elif e.window.network and \
            target[0:1] in (e.window.network.isupport.get('CHANTYPES') or '&#$+'):
        
        is_chan(e, target)

def onListRightClick(e):
    is_nick(e, e.nick)
