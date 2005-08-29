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
    
    if msg[0][0] == ":":
        msg[0] = msg[0][1:]
    else:
        msg.insert(0, server)
    
    for i, token in enumerate(msg):
        if token and token[0] == ":":
            msg = msg[:i] + [" ".join([token[1:]] + msg[i+1:])]
            break
    
    return [m for m in msg[:-1] if m] + msg[-1:]

class Network:
    socket = None               # this network's socket
    socket_id = None            # the list of id's used to disable our callbacks
    writeable_id = None         # the id used to disable the on_writeable cb
    
    buffer = ''              # data we've received but not processed yet
    
    nicks = []                  # desired nicknames
    fullname = ""               # our full name
    
    server = None
    port = 6667
    password = ''
    
    status = DISCONNECTED
    name = ''
    
    me = ''                     # my nickname
    channels = None             # dictionary of channels we're on on this network
    
    channel_prefixes = '&#+$'   # from rfc2812
    
    def __init__(self, server, port=6667, nicks=[], fullname=""):
        self.server = server
        self.port = port
        
        if conf.get("nick"):
            def_nicks = [conf.get("nick")]
        else:
            def_nicks = ["MrUrk"]
        
        self.nicks = nicks or def_nicks
        self.me = self.nicks[0]
            
        self.fullname = fullname or "Urk user"

        self.channels = {}
    
    #called when we can write to the socket
    def on_writeable(self):
        #test the socket for writeability--we might be disconnected
        try:
            self.socket.send('')
        except socket.error, (number, detail):
            self.disconnect(error=detail)
            return True
        except:
            self.disconnect(error="Network error!")
            return True
            
        self.status = INITIALIZING
        
        ui.unregister(self.writeable_id)
        self.writeable_id = None
    
        e_data = events.data()
        e_data.network = self
        e_data.type = "socket_connect"
        events.trigger('SocketConnect', e_data)
        
        return True
    
    #called when we can read from the socket
    def on_readable(self):
        reply = self.socket.recv(8192)
        
        if reply:
            self.buffer = self.buffer + reply
            
            lines, self.buffer = self.buffer.rsplit("\r\n",1)
            
            for line in lines.split('\r\n'):
                if DEBUG:
                    print ">>> %s" % line

                self.got_msg(line)
        else:
            try:
                self.socket.send('')
            except socket.error, (number, detail):
                self.disconnect(error=detail)
            except:
                self.disconnect(error="Network error!")
        
        return True
        
    #called when there's a socket error
    def on_error(self):
        #we should get the error from the socket so we can report it, but I
        # don't know how!
        try:
            self.socket.send('')
        except socket.error, (number, detail):
            self.disconnect(error=detail)
        except:
            self.disconnect(error="Network error!")
        
        return True
        
    #called when the socket is disconnected
    def on_disconnect(self):
        self.disconnect()
        
        return True
        
    def raw(self, msg):
        if DEBUG:
            print ">>> %s" % (msg + "\r\n").replace("\r\n", "\\r\\n")
    
        self.socket.send(msg + "\r\n")
        
    def got_msg(self, msg):
        e_data = events.data()
        e_data.rawmsg = msg
        e_data.msg = parse_irc(msg, self.server)
        e_data.text = e_data.msg[-1]
        e_data.network = self
        e_data.window = ui.get_status_window(self)
        e_data.type = "raw"
        
        source = e_data.msg[0].split('!')
        e_data.source = source[0]
        
        if len(source) > 1:
            e_data.address = source[1]
        else:
            e_data.address = ''
        
        if len(e_data.msg) > 2:
            e_data.target = e_data.msg[2]
        else:
            e_data.target = e_data.msg[-1]
        
        events.trigger('Raw', e_data)
    
    def connect(self):
        if not self.status:
            self.status = CONNECTING
            self.socket = socket.socket()
            self.socket.settimeout(0)
            
            self.writeable_id = ui.register_io(self.on_writeable,self.socket,ui.IO_OUT)
            self.socket_id = (
                ui.register_io(self.on_readable,self.socket,ui.IO_IN),
                ui.register_io(self.on_error,self.socket,ui.IO_ERR),
                ui.register_io(self.on_disconnect,self.socket,ui.IO_HUP),
                )
            
            try:
                self.socket.connect((self.server, self.port))
            except socket.error:
                #this is probably telling us we're not connected just yet
                pass
            
            e_data = events.data()
            e_data.network = self
            e_data.type = "connecting"            
            events.trigger('Connecting', e_data)
    
    def disconnect(self, error=None):
        if self.writeable_id:
            ui.unregister(self.writeable_id)
            self.writeable_id = None
        if self.socket_id:
            for socket_id in self.socket_id:
                ui.unregister(socket_id)
                self.socket_id = None
        
        self.socket = None
        
        self.status = DISCONNECTED
        
        #note: connecting from onDisconnect is probably a Bad Thing
        e_data = events.data()
        e_data.network = self
        e_data.error = error
        e_data.type = "disconnect"
        events.trigger('Disconnect', e_data)
        
        #trigger a nick change if the nick we want is different from the one we
        # had.
        if self.me != self.nicks[0]:
            e_data = events.data()
            e_data.network = self
            e_data.window = ui.get_status_window(self)
            e_data.source = self.me
            e_data.newnick = self.nicks[0]
            e_data.type = 'nick'
            events.trigger('Nick', e_data)
            self.me = self.nicks[0]
        
    def normalize_case(self, string):
        return string.lower()
    
    def quit(self,msg=None):
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
        e_data = events.data()
        e_data.source = self.me
        e_data.target = str(target)
        e_data.text = msg
        e_data.type = 'text'
        e_data.network = self
        e_data.window = ui.get_status_window(self)
        events.trigger('Text', e_data)

    def emote(self, target, msg):
        self.raw("PRIVMSG %s :\x01ACTION %s\x01" % (target, msg))
        e_data = events.data()
        e_data.source = self.me
        e_data.target = str(target)
        e_data.text = msg
        e_data.type = 'action'
        e_data.network = self
        e_data.window = ui.get_status_window(self)
        events.trigger('Action', e_data)

    def notice(self, target, msg):
        self.raw("NOTICE %s :%s" % (target, msg))
        e_data = events.data()
        e_data.source = self.me
        e_data.target = str(target)
        e_data.text = msg
        e_data.type = 'ownnotice'
        e_data.network = self
        e_data.window = ui.get_status_window(self)
        events.trigger('OwnNotice', e_data)
