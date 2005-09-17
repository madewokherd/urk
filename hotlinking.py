import events
import ui

def onClick(event):
    # click on a #channel
    if event.target.startswith("#"):
        if event.target not in event.window.network.channels:
            event.window.network.join(event.target)
        
    # nick on this channel
    target_l = event.target.lstrip('@+%.(<')
    target_fr = event.target_fr + len(event.target) - len(target_l)
    
    target_r = event.target.rstrip(')>:,')
    target_to = event.target_to - len(event.target) + len(target_r)
    
    target = event.text[target_fr:target_to]
    
    if type(event.window) == ui.ChannelWindow and \
            target in event.window.network.channels[event.window.id].nicks:
        events.run_command("query %s" % target, event.window, event.window.network)
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    if (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        if target.startswith("www"):
            target = "http://"+target
        ui.open_file(target)

def onHover(event):
    # click on a #channel
    if event.target.startswith("#"):
        event.tolink.add((event.target_fr, event.target_to))
        return
        
    # nick on this channel
    target_l = event.target.lstrip('@+%.(<')
    target_fr = event.target_fr + len(event.target) - len(target_l)
    
    target_r = event.target.rstrip(')>:,')
    target_to = event.target_to - len(event.target) + len(target_r)
    
    target = event.text[target_fr:target_to]
    
    if type(event.window) == ui.ChannelWindow and \
            target in event.window.network.channels[event.window.id].nicks:
        event.tolink.add((target_fr, target_to))        
    
    # url of the form http://xxx.xxx or www.xxx.xxx       
    elif (target.startswith("http://") and target.count(".") >= 1) or \
            target.startswith("www") and target.count(".") >= 2:
        event.tolink.add((target_fr, target_to))

