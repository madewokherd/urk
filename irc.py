import socket
import thread
import sys
import traceback

import conf
import events
import __main__ as urk

DEBUG = 1

def parse_irc(message, server):
    result = []
    
    message = message.rstrip()
    
    if message[0] == ":":
        i = message.find(" ")
        if i != -1:
            result.append(message[1:i])
            message = message[i+1:]
        else:
            result.append(message[1:])
            return result
    else:
        result.append(server)
        
    message = message.lstrip(" ")
        
    while message:
        if message[0] == ":":
            result.append(message[1:])
            return result
            
        else:
            i = message.find(" ")
            if i != -1:
                result.append(message[0:i])
                message = message[i+1:]
            else:
                result.append(message[0:])
                return result
                
        message = message.lstrip(" ")
            
    return result

def handle_connect(network):
    socket = network.sock
    address = network.server, network.port

    try:
        socket.connect(address)
        
        network.initializing = True
        
        e_data = events.data()
        e_data.network = network
        e_data.type = "socket_connect"
        events.trigger('SocketConnect', e_data)
         
        reply = socket.recv(8192)
        in_buffer = reply
            
        while reply:
            while 1:
                pos = in_buffer.find("\r\n")
                if pos == -1:
                    break
                line = in_buffer[0:pos]
                in_buffer = in_buffer[pos+2:]
                
                if DEBUG:
                    print ">>> %s" % line

                try:
                    network.got_msg(line)
                except:
                    print "Error processing incoming text: "+line
                    traceback.print_exception(*sys.exc_info())
            
            reply = socket.recv(8192)
            in_buffer += reply
    except:
        error = sys.exc_info()
    else:
        error = None
    network.connecting = False
    network.initializing = False
    
    e_data = events.data()
    e_data.network = network
    e_data.error = error
    e_data.type = "disconnect"
    events.trigger('Disconnect', e_data)

class Network:
    sock = None                 # this networks socket
    
    nicks = []                  # desired nicknames
    fullname = ""               # our full name
    
    server = None
    port = 6667
    password = ''
    
    connecting = False
    initializing = False
    connected = False
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
            
        self.fullname = fullname or "Urk user"

        self.channels = {}
        
        print self.nicks
        
    def raw(self, msg):
        if DEBUG:
            print ">>> %s" % (msg + "\r\n").replace("\r\n", "\\r\\n")
    
        self.sock.send(msg + "\r\n")
        
    def got_msg(self, msg):
        e_data = events.data()
        e_data.rawmsg = msg
        e_data.msg = parse_irc(msg, self.server)
        e_data.text = e_data.msg[-1]
        e_data.network = self
        e_data.window = urk.get_window[self]
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
    
    #this is probably not necessary
    #def onDisconnect(self, **kwargs):
        # this needs to be set before the event in case we autoreconnect on 
        # disconnect or something
        #
        #self.connecting = False
        #dispatch.DisconnectIrc(self, **kwargs)
    
    def connect(self):
        if not self.connecting:
            self.connecting = True
            self.sock = socket.socket()
            
            thread.start_new_thread(handle_connect, (self,))
            
            e_data = events.data()
            e_data.network = self
            e_data.type = "connecting"            
            events.trigger('Connecting', e_data)
            
    def normalize_case(self, string):
        return string.lower()
    
    def quit(self,msg="."):
        self.raw("QUIT :%s" % msg)
        
    def disconnect(self,msg="."):
        self.raw("QUIT :%s" % msg)
        
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
        e_data.window = urk.get_window[self]
        events.trigger('Text', e_data)

    def emote(self, target, msg):
        self.raw("PRIVMSG %s :\x01ACTION %s\x01" % (target, msg))
        e_data = events.data()
        e_data.source = self.me
        e_data.target = str(target)
        e_data.text = msg
        e_data.type = 'action'
        e_data.network = self
        e_data.window = urk.get_window[self]
        events.trigger('Action', e_data)

    def notice(self, target, msg):
        self.raw("NOTICE %s :%s" % (target, msg))
        e_data = events.data()
        e_data.source = self.me
        e_data.target = str(target)
        e_data.text = msg
        e_data.type = 'ownnotice'
        e_data.network = self
        e_data.window = urk.get_window[self]
        events.trigger('OwnNotice', e_data)
