import socket
import sys

import conf
import events
import __main__ as urk
import ui

DEBUG = 0

DISCONNECTED = 0
CONNECTING = 1
INITIALIZING = 2
CONNECTED = 3

def parse_irc(msg, server):
    msg = msg.split(" ")
    
    # if our very first character is :
    # then this is the source, 
    # otherwise insert the server as the source
    if msg[0][0] == ":":
        msg[0] = msg[0][1:]
    else:
        msg.insert(0, server)
    
    # loop through the msg until we find 
    # something beginning with :
    for i, token in enumerate(msg):
        if token.startswith(":"):
            # remove the :
            msg[i] = msg[i][1:]
            
            # join up the rest
            msg[i:] = [" ".join(msg[i:])]
            break
    
    # filter out the empty pre-":" tokens and add on the text to the end
    return [m for m in msg[:-1] if m] + msg[-1:]
    
    # note: this sucks and makes very little sense, but it matches the BNF
    #       as far as we've tested, which seems to be the goal

class Network:
    # desired nicknames
    try:
        import getpass
        nicks = (conf.get("nick") or getpass.getuser(),)
        del getpass
    except:
        nicks = ("mrurk",)
    
    def __init__(self, server="irc.default.org", port=6667, nicks=[], fullname=""):
        self.server = server
        self.port = port
        
        self.nicks = nicks or list(self.nicks)
        self.me = self.nicks[0]
        
        self.fullname = fullname or "urk user"
        self.password = ''
        
        self.isupport = {
            'NETWORK': server, 
            'PREFIX': '(ohv)@%+',
            'CHANMODES': 'b,k,l,imnpstr',
        }
        self.prefixes = {'o':'@', 'h':'%', 'v':'+', '@':'o', '%':'h', '+':'v'}
        
        self.status = DISCONNECTED
        self.channel_prefixes = '&#+$'   # from rfc2812
        
        self.buffer = ''
    
    #called when socket.open() returns
    def on_connect(self, result, error):
        if error:
            self.disconnect(error=error[1])
        else:
            self.status = INITIALIZING
            
            e_data = events.data()
            e_data.network = self
            events.trigger('SocketConnect', e_data)
            
            self.source_id = ui.fork(self.on_read, self.socket.recv, 8192)
    
    #called when we read data or failed to read data
    def on_read(self, result, error):
        if error:
            print error[0]
            print error.args
            self.disconnect(error=error[1])
        elif not result:
            self.disconnect(error="Connection closed by remote host")
        else:
            self.buffer += result
            
            lines, self.buffer = self.buffer.rsplit("\r\n", 1)
            
            for line in lines.split('\r\n'):
                if DEBUG:
                    print "<<< %s" % line
        
                self.got_msg(line)            
            
            self.source_id = ui.fork(self.on_read, self.socket.recv, 8192)

    def raw(self, msg):
        if DEBUG:
            print ">>> %s" % (msg + "\r\n").replace("\r\n", "\\r\\n")
    
        self.socket.send(msg + "\r\n")
        
    def got_msg(self, msg):
        pmsg = parse_irc(msg, self.server)
    
        e_data = events.data(
                    msg=pmsg,
                    text=pmsg[-1],
                    network=self,
                    window=ui.get_default_window(self)
                    )
        
        if "!" in pmsg[0]:
            e_data.source, e_data.address = pmsg[0].split('!')
            
        else:
            e_data.source, e_data.address = pmsg[0], ''
        
        if len(pmsg) > 2:
            e_data.target = pmsg[2]
        else:
            e_data.target = pmsg[-1]
        
        events.trigger('Raw', e_data)
    
    def connect(self):
        if not self.status:
            self.status = CONNECTING
            self.socket = socket.socket()
            
            self.source_id = \
                ui.fork(self.on_connect, self.socket.connect, (self.server, self.port))
            
            e_data = events.data()
            e_data.network = self
            events.trigger('Connecting', e_data)
    
    def disconnect(self, error=None):
        self.socket.close()

        if self.source_id:
            ui.unregister(self.source_id)
            self.source_id = None
        
        self.socket = None
        
        self.status = DISCONNECTED
        
        #note: connecting from onDisconnect is probably a Bad Thing
        events.trigger(
            'Disconnect', 
            events.data(network=self, error=error)
            )
        
        #trigger a nick change if the nick we want is different from the one we
        # had.
        if self.me != self.nicks[0]:
            e_data = events.data(
                        network=self,
                        window=ui.get_default_window(self),
                        source=self.me,
                        newnick=self.nicks[0]
                        )
            events.trigger('Nick', e_data)
            self.me = self.nicks[0]
        
    def norm_case(self, string):
        return string.lower()
    
    def quit(self,msg=None):
        if self.status:
            try:
                if msg == None:
                    msg = conf.get('quitmsg')
                    if msg == None:
                        msg = "%s - %s" % (urk.long_version, urk.website)
                self.raw("QUIT :%s" % msg)
            except:
                pass
            self.disconnect()
        
    def join(self, name):        
        self.raw("JOIN %s" % name)
        
    def part(self, target, msg=""):
        if msg:
            msg = " :" + msg
        
        self.raw("PART %s%s" % (target, msg))
        
    def msg(self, target, msg):
        self.raw("PRIVMSG %s :%s" % (target, msg))
        
        e_data = events.data(
                    source=self.me,
                    target=str(target),
                    text=msg,
                    network=self,
                    window=ui.get_default_window(self)
                    )
        events.trigger('OwnText', e_data)

    def notice(self, target, msg):
        self.raw("NOTICE %s :%s" % (target, msg))
        
        e_data = events.data(
                    source=self.me,
                    target=str(target),
                    text=msg,
                    network=self,
                    window=ui.get_default_window(self)
                    )
        events.trigger('OwnNotice', e_data)
