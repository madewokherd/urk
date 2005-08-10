import socket
import thread
import weakref
import sys
import traceback

import gtk

import events
import __main__ as urk

DEBUG = 0

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

def handle_connect(socket, network, address):
    try:
        socket.connect(address)
        
        network.initializing = True
        events.trigger('SocketConnect', events.data(network=network, type='socket_connect'))
         
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
                
                #gtk.gdk.threads_enter()
                try:
                    network.got_msg(line)
                except:
                    print "Error processing incoming text: "+line
                    traceback.print_exception(*sys.exc_info())
                #gtk.gdk.threads_leave()
            
            reply = socket.recv(8192)
            in_buffer += reply
    except:
        error = sys.exc_info()
    else:
        error = None
    network.connecting = False
    network.initializing = False

    events.trigger('Disconnect', events.data(network=network, error=error, type='disconnect'))

class Network:
    sock = None
    
    nick = "" # not necessarily my nick, just the one I want
    anicks = ('MrUrk',) # other nicks I might want
    fullname = ""
    email = ""
    
    server = None
    port = 6667
    password = ''
    
    connecting = False
    initializing = False
    connected = False
    #name = ''
    
    me = None # me as a user
    channels = None #set of channels I'm on
    
    #network-specific data
    channel_prefixes = '&#+$' #from rfc2812
    
    def __init__(self, fullname, nick, server, port=6667):
        #self.sock = socket.socket()
        
        self.fullname = fullname
        self.nick = nick
        
        self.server = server
        self.port = port
        
        self._entities = weakref.WeakValueDictionary()
        self.channels = set()
        
    def raw(self, msg):
        msg = msg + "\r\n"
    
        if DEBUG:
            print ("<<< %s" % msg.replace("\r\n", "\\r\\n"))
        
        self.sock.send(msg)
        
    def got_msg(self, msg):
        data = events.data()
        data.rawmsg = msg
        data.msg = parse_irc(msg, self.server)
        data.text = data.msg[-1]
        data.network = self
        data.window = urk.get_window[self]
        data.type = "raw"
        
        source = data.msg[0].split('!')
        data.source = source[0]
        
        if len(source) > 1:
            data.address = source[1]
        else:
            data.address = ''
        
        if len(data.msg) > 2:
            data.target = data.msg[2]
        else:
            data.target = data.msg[-1]
        
        events.trigger('Raw', data)
    
    #this is probably not necessary
    #def onDisconnect(self, **kwargs):
        #this needs to be set before the event in case we autoreconnect on disconnect or something
        #self.connecting = False
        #dispatch.DisconnectIrc(self, **kwargs)
    
    def connect(self):
        if not self.connecting:
            self.connecting = True
            self.sock = socket.socket()
            
            args = self.sock, self, (self.server, self.port)
            thread.start_new_thread(handle_connect, args)
            
            events.trigger('Connecting', events.data(network=self, type='connecting'))
            
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
