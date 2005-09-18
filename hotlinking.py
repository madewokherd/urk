import events
import ui

def onClick(e):
    # click on a #channel
    if e.target.startswith("#"):
        if e.target not in e.window.network.channels:
            e.window.network.join(e.target)
        
    # nick on this channel
    target_l = e.target.lstrip('@+%.(<')
    target_fr = e.target_fr + len(e.target) - len(target_l)
    
    target_r = e.target.rstrip(')>:,')
    target_to = e.target_to - len(e.target) + len(target_r)
    
    target = e.text[target_fr:target_to]
    
    if type(e.window) == ui.ChannelWindow and \
            target in e.window.network.channels[e.window.id].nicks:
        events.run_command("query %s" % target, e.window, e.window.network)
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    if (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        if target.startswith("www"):
            target = "http://"+target
        ui.open_file(target)

def onHover(e):
    # click on a #channel
    if e.target.startswith("#"):
        e.tolink.add((e.target_fr, e.target_to))
        return
        
    # nick on this channel
    target_l = e.target.lstrip('@+%.(<')
    target_fr = e.target_fr + len(e.target) - len(target_l)
    
    target_r = e.target.rstrip(')>:,')
    target_to = e.target_to - len(e.target) + len(target_r)
    
    target = e.text[target_fr:target_to]
    
    if type(e.window) == ui.ChannelWindow and \
            target in e.window.network.channels[e.window.id].nicks:
        e.tolink.add((target_fr, target_to))        
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        e.tolink.add((target_fr, target_to))

