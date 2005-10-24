import time

import ui
import chaninfo

DATE_FORMAT_LONG = '%Y-%m-%d %H:%M:%S (%Z)'
DATE_FORMAT = '%m-%d %H:%M'

def onText(e):
    e.network, e.window.id
    
    print time.strftime(DATE_FORMAT), '<%s> %s' % (e.source, e.text)

def onOwnText(e):
    e.network, e.window.id
    
    print time.strftime(DATE_FORMAT), '<%s> %s' % (e.source, e.text)
    
def onAction(e):
    e.network, e.window.id
    
    print time.strftime(DATE_FORMAT), '*%s %s' % (e.source, e.text)

def onOwnAction(e):
    e.network, e.window.id
    
    print time.strftime(DATE_FORMAT), '*%s %s' % (e.source, e.text)

def onNotice(e):
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
        
    e.network, window.id

    print time.strftime(DATE_FORMAT), '-%s- %s' % (e.source, e.text)

def onOwnNotice(e):
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
        
    e.network, window.id

    print time.strftime(DATE_FORMAT), '-%s- %s' % (e.source, e.text)

def onCtcp(e):
    if not e.quiet:
        e.network, e.source
        
        print time.strftime(DATE_FORMAT), '[%s] %s' % (e.source, e.text)

def onCtcpReply(e):
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
        
    e.network, window.id

    print time.strftime(DATE_FORMAT), '--- %s reply from %s: %s' % (e.name.capitalize(), e.source, ' '.join(e.args))

def onJoin(e):
    e.network, e.window.id

    if e.network.me == e.source:
        # START A NEW LOG FILE HERE OMG
        print e.network.me, time.strftime(DATE_FORMAT_LONG)
        to_write = time.strftime(DATE_FORMAT), 'You joined %s' % e.target

    else:
        to_write = '\x02%s\x02 (%s) joined %s' % (e.source, e.address, e.target)
        
    print time.strftime(DATE_FORMAT), to_write

def onPart(e):
    e.network, e.window.id

    if e.network.me == e.source:
        to_write = 'You left %s' % e.target
    else:
        to_write = '%s (%s) left %s' % (e.source, e.address, e.target)
        
    if e.text:
        to_write += ' (%s)' % e.text
    
    print time.strftime(DATE_FORMAT), to_write

def onKick(e):
    e.network, e.window.id

    print time.strftime(DATE_FORMAT), '%s kicked %s (%s)' % (e.source, e.target, e.text)
        
def onMode(e):
    e.network, e.window.id
    
    print time.strftime(DATE_FORMAT), '%s sets mode: %s' % (e.source, e.text)
        
def onQuit(e):
    to_write = "%s quit (%s)" % (e.source, e.text)
    
    for channame in chaninfo.channels(e.network):
        if chaninfo.ison(e.network, channame, e.source):
            window = ui.windows.get(ui.ChannelWindow, e.network, channame)
            if window:
                e.network, window.id
                
                print time.strftime(DATE_FORMAT), to_write

def onNick(e):
    if e.source == e.network.me:
        to_write = 'You are now known as %s' % e.newnick
    
        for window in ui.get_window_for(network=e.network):
            print time.strftime(DATE_FORMAT), to_write
    else:
        to_write = '%s is now known as %s' % (e.source, e.newnick)
    
        for channame in chaninfo.channels(e.network):
            if chaninfo.ison(e.network,channame,e.source):
                window = ui.windows.get(ui.ChannelWindow, e.network, channame)
                if window:
                    e.network, window.id
                    
                    print time.strftime(DATE_FORMAT), to_write

def onTopic(e):
    e.network, e.window.id
    
    print time.strftime(DATE_FORMAT), '%s set topic on %s: %s' % (e.source, e.target, e.text)

def onRaw(e):
    if not e.quiet:
        if e.msg[1].isdigit():
            if e.msg[1] == '332':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                
                e.network, window.id
                
                print time.strftime(DATE_FORMAT), 'topic on %s is: %s' % (e.msg[3], e.text)
                
            elif e.msg[1] == '333':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                
                e.network, window.id
                
                print time.strftime(DATE_FORMAT), 'topic on %s set by %s at time %s' % (e.msg[3], e.msg[4], time.ctime(int(e.msg[5])))
            
            elif e.msg[1] == '329': #RPL_CREATIONTIME
                pass
            
            else:
                e.network, e.window.id
            
                print time.strftime(DATE_FORMAT), '* %s' % ' '.join(e.msg[3:])

        elif e.msg[1] == 'ERROR':
            e.network, e.window.id
            
            print time.strftime(DATE_FORMAT), 'Error: %s' % e.text

def onDisconnect(e):
    if e.error:
        to_write = '* Disconnected (%s)' % e.error
    else:
        to_write = '* Disconnected'

    for window in ui.get_window_for(network=e.network):
        e.network, window.id
        
        print time.strftime(DATE_FORMAT), to_write
