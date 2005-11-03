import time
import os

from conf import conf
import ui
import chaninfo
import __main__ as urk

DATE_FORMAT_LONG = '%Y-%m-%d.%H %M:%S (%Z)'
DATE_FORMAT = '%m-%d %H:%M'

LOG_DIR = conf['log_dir'] or os.path.join(urk.userpath,'logs')
if not os.access(LOG_DIR, os.F_OK):
    os.mkdir(LOG_DIR)
    
def log_file(network, name, new=False):
    network_dir = os.path.join(LOG_DIR, network.name)
    if not os.access(network_dir, os.F_OK):
        os.mkdir(network_dir)
    
    name_dir = os.path.join(LOG_DIR, network.name, name)    
    if not os.access(name_dir, os.F_OK):
        os.mkdir(name_dir)
       
    if new:
        recent_log = time.strftime('%Y-%m-%d.%H%M%S.log')
    else:
        try:
            recent_log = sorted(os.listdir(name_dir))[-1]
        except IndexError:
            recent_log = time.strftime('%Y-%m-%d %H%M%S.log')

    return LogFile(os.path.join(name_dir, recent_log), 'a')
    
class LogFile(file):
    def write(self, text):
        file.write(self, '%s %s%s' % (time.strftime(DATE_FORMAT), text, os.linesep))

def onText(e):
    f = log_file(e.network, e.window.id)
    
    f.write('<%s> %s' % (e.source, e.text))

def onOwnText(e):
    f = log_file(e.network, e.window.id)
    
    f.write('<%s> %s' % (e.source, e.text))
    
def onAction(e):
    f = log_file(e.network, e.window.id)
    
    f.write('*%s %s' % (e.source, e.text))

def onOwnAction(e):
    f = log_file(e.network, e.window.id)
    
    f.write('*%s %s' % (e.source, e.text))

def onNotice(e):
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
        
    f = log_file(e.network, window.id)

    f.write('-%s- %s' % (e.source, e.text))

def onOwnNotice(e):
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
        
    f = log_file(e.network, window.id)

    f.write('-%s- %s' % (e.source, e.text))

def onCtcp(e):
    if not e.quiet:
        f = log_file(e.network, e.source)
        
        f.write('[%s] %s' % (e.source, e.text))

def onCtcpReply(e):
    window = ui.windows.manager.get_active()
    if window.network != e.network:
        window = ui.get_default_window(e.network)
        
    f = log_file(e.network, window.id)

    f.write('--- %s reply from %s: %s' % (e.name.capitalize(), e.source, ' '.join(e.args)))

def onJoin(e):
    if e.network.me == e.source:   
        # START A NEW LOG FILE HERE OMG
        f = log_file(e.network, e.window.id, new=True)
        f.write('%s %s' % (e.network.me, time.strftime(DATE_FORMAT_LONG)))

        to_write = 'You joined %s' % e.target

    else:
        f = log_file(e.network, e.window.id)
        to_write = '\x02%s\x02 (%s) joined %s' % (e.source, e.address, e.target)
        
    f.write(to_write)

def onPart(e):
    f = log_file(e.network, e.window.id)

    if e.network.me == e.source:
        to_write = 'You left %s' % e.target
    else:
        to_write = '%s (%s) left %s' % (e.source, e.address, e.target)
        
    if e.text:
        to_write += ' (%s)' % e.text
    
    f.write(to_write)

def onKick(e):
    f = log_file(e.network, e.window.id)

    f.write('%s kicked %s (%s)' % (e.source, e.target, e.text))
        
def onMode(e):
    f = log_file(e.network, e.window.id)
    
    f.write('%s sets mode: %s' % (e.source, e.text))
        
def onQuit(e):
    to_write = "%s quit (%s)" % (e.source, e.text)
    
    for channame in chaninfo.channels(e.network):
        if chaninfo.ison(e.network, channame, e.source):
            window = ui.windows.get(ui.ChannelWindow, e.network, channame)
            if window:
                f = log_file(e.network, window.id)
                
                f.write(to_write)

def onNick(e):
    if e.source == e.network.me:
        to_write = 'You are now known as %s' % e.newnick
    
        for window in ui.get_window_for(network=e.network):
            f.write(to_write)
    else:
        to_write = '%s is now known as %s' % (e.source, e.newnick)
    
        for channame in chaninfo.channels(e.network):
            if chaninfo.ison(e.network,channame,e.source):
                window = ui.windows.get(ui.ChannelWindow, e.network, channame)
                if window:
                    f = log_file(e.network, window.id)
                    
                    f.write(to_write)

def onTopic(e):
    f = log_file(e.network, e.window.id)
    
    f.write('%s set topic on %s: %s' % (e.source, e.target, e.text))

def onRaw(e):
    if not e.quiet:
        if e.msg[1].isdigit():
            if e.msg[1] == '332':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                
                f = log_file(e.network, window.id)
                
                f.write('topic on %s is: %s' % (e.msg[3], e.text))
                
            elif e.msg[1] == '333':
                window = ui.windows.get(ui.ChannelWindow, e.network, e.msg[3]) or e.window
                
                f = log_file(e.network, window.id)
                
                f.write('topic on %s set by %s at time %s' % (e.msg[3], e.msg[4], time.ctime(int(e.msg[5]))))
            
            elif e.msg[1] == '329': #RPL_CREATIONTIME
                pass
            
            else:
                f = log_file(e.network, e.window.id)
            
                f.write('* %s' % ' '.join(e.msg[3:]))

        elif e.msg[1] == 'ERROR':
            f = log_file(e.network, e.window.id)
            
            f.write('Error: %s' % e.text)

def onDisconnect(e):
    if e.error:
        to_write = '* Disconnected (%s)' % e.error
    else:
        to_write = '* Disconnected'

    for window in ui.get_window_for(network=e.network):
        f = log_file(e.network, window.id)
        
        f.write(to_write)
