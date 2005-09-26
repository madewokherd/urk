import events
import ui
import chaninfo

def onClick(e):
    # nick on this channel
    target_l = e.target.lstrip('@+%.(<')
    target_fr = e.target_fr + len(e.target) - len(target_l)
    
    target_r = e.target.rstrip(')>:,')
    target_to = e.target_to - len(e.target) + len(target_r)
    
    target = e.text[target_fr:target_to]
    
    if type(e.window) == ui.ChannelWindow and \
            chaninfo.ison(e.window.network, e.window.id, target):
        events.run_command("query %s" % target, e.window, e.window.network)
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        if target.startswith("www"):
            target = "http://"+target
        ui.open_file(target)
    
    # click on a #channel
    elif target and e.window.network and \
            target[0] in (e.window.network.isupport.get('CHANTYPES') or '&#$+'):
        if not chaninfo.ischan(e.window.network, target):
            e.window.network.join(target)

def onHover(e):
    # nick on this channel
    target_l = e.target.lstrip('@+%.(<')
    target_fr = e.target_fr + len(e.target) - len(target_l)
    
    target_r = e.target.rstrip(')>:,')
    target_to = e.target_to - len(e.target) + len(target_r)
    
    target = e.text[target_fr:target_to]
    
    if type(e.window) == ui.ChannelWindow and \
            chaninfo.ison(e.window.network, e.window.id, target):
        e.tolink.add((target_fr, target_to))        
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        e.tolink.add((target_fr, target_to))
    
    # click on a #channel
    elif target and e.window.network and \
            target[0] in (e.window.network.isupport.get('CHANTYPES') or '&#$+'):
        e.tolink.add((target_fr, target_to))
