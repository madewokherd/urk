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

def handle_connect(socket, init, network, address):
    try:
        socket.connect(address)
        
        init()
         
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
    events.trigger('Disconnect', events.data(network=network, error=error))

class Network:
    sock = None
    
    nick = "" # not necessarily my nick, just the one I want
    anicks = None # other nicks I might want
    fullname = ""
    email = ""
    
    server = None
    port = 6667
    password = ''
    
    connecting = False
    #name = ''
    
    me = None # me as a user
    _users = None
    _channels = None
    channels = None #set of channels I'm on
    
    def __init__(self, fullname, nick, server, port=6667):
        #self.sock = socket.socket()
        
        self.fullname = fullname
        self.nick = nick
        
        self.server = server
        self.port = port
        
        self._users = weakref.WeakValueDictionary()
        self._channels = weakref.WeakValueDictionary()
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
        data.network = self
        data.window = urk.get_window[self]

        events.trigger('Raw', data)
    
    #this is probably not necessary
    #def onDisconnect(self, **kwargs):
        #this needs to be set before the event in case we autoreconnect on disconnect or something
        #self.connecting = False
        #dispatch.DisconnectIrc(self, **kwargs)
    
    def connect(self):
        def init():
            events.trigger('SocketConnect', events.data(network=self))

        if not self.connecting:
            self.connecting = True
            self.sock = socket.socket()
            
            args = self.sock, init, self, (self.server, self.port)
            thread.start_new_thread(handle_connect, args)
            
            events.trigger('Connecting', events.data(network=self))
            
    def normalize_case(self, string):
        return string.lower()
    
    #returns a User object for the user
    def user(self, name):
        normal_name = self.normalize_case(name)
        result = self._users.get(normal_name)
        if not result:
            result = User()
            result.name = name
            result.normal_name = normal_name
            result.network = self
            self._users[normal_name] = result
        return result
    
    #returns a User or Channel
    def entity(self, name):
        normal_name = self.normalize_case(name)
        result = self._channels.get(normal_name)
        if not result:
            result = self._users.get(normal_name)
            if not result:
                result = User()
                result.name = name
                result.normal_name = normal_name
                result.network = self
                self._users[normal_name] = result
        return result
    
    #returns a Channel
    def channel(self, name):
        normal_name = self.normalize_case(name)
        result = self._channels.get(normal_name)
        if not result:
            result = Channel()
            result.name = name
            result.normal_name = normal_name
            result.network = self
            self._channels[normal_name] = result
        return result
    
    #I'm not sure I like these, but there doesn't seem to be a reason to get
    # rid of them just yet. -MEH
    def quit(self,msg="."):
        self.raw("QUIT :%s" % msg)
        
    def disconnect(self,msg="."):
        self.raw("QUIT :%s" % msg)
        
    def join(self, name):        
        self.raw("JOIN %s" % name)
        
    def part(self, name, msg=""):
        if msg:
            msg = " :" + msg
        
        self.raw("PART %s%s" % (name, msg))
        
    def msg(self, name, msg):
        self.raw("PRIVMSG %s :%s" % (name, msg))
        
class Channel:
    nicks = None
    type = "channel"
    
    name = ""
    normal_name = ""
    address = ""
    network = ""
    # window = None
    
    def __eq__(self,oth):
        if hasattr(oth,'normal_name'):
            return self.normal_name == oth.normal_name
        else:
            return self.normal_name == self.network.normalize_case(str(oth))
    
    def __init__(self):
        self.nicks = []
    
    def __hash__(self):
        return hash(self.normal_name)

    def __repr__(self):
        return "<User instance "+repr(self.name)+">"
    
    def __str__(self):
        return self.name
    
    def add(self, user):
        self.nicks.append(user)
        
    def remove(self, user):
        self.nicks = [u for u in self.nicks if u != user]

class User:
    type = "user"
    name = ""
    normal_name = ""
    address = ""
    network = ""
    # window = None
    
    def __eq__(self,oth):
        if hasattr(oth,'normal_name'):
            return self.normal_name == oth.normal_name
        else:
            return self.normal_name == self.network.normalize_case(str(oth))

    def __hash__(self):
        return hash(self.normal_name)

    def __repr__(self):
        return "<User instance "+repr(self.name)+">"
    
    def __str__(self):
        return self.name
