import socket
import errno
import sys
import os

from conf import conf
import events
import urk
import ui
import windows

DISCONNECTED = 0
CONNECTING = 1
INITIALIZING = 2
CONNECTED = 3

def parse_irc(msg, server):
    msg = msg.split(' ')
    
    # if our very first character is :
    # then this is the source, 
    # otherwise insert the server as the source
    if msg[0][0] == ':':
        msg[0] = msg[0][1:]
    else:
        msg.insert(0, server)
    
    # loop through the msg until we find 
    # something beginning with :
    for i, token in enumerate(msg):
        if token.startswith(':'):
            # remove the :
            msg[i] = msg[i][1:]
            
            # join up the rest
            msg[i:] = [' '.join(msg[i:])]
            break
    
    # filter out the empty pre-":" tokens and add on the text to the end
    return [m for m in msg[:-1] if m] + msg[-1:]
    
    # note: this sucks and makes very little sense, but it matches the BNF
    #       as far as we've tested, which seems to be the goal

def default_nicks():
    try:
        nicks = [conf.get('nick')]
        if not nicks[0]:
            import getpass
            nicks = [getpass.getuser()]
    except:
        nicks = ["mrurk"]
    return nicks

class Network(object):
    socket = None
    DEBUG = False
    
    def __init__(self, server="irc.default.org", port=6667, nicks=[], 
                    fullname="", name=None, **kwargs):
        self.server = server
        self.port = port
        
        self.name = name or server
        
        self.nicks = nicks or default_nicks()
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
        self.failedhosts = [] #hosts we've tried and failed to connect to
        self.channel_prefixes = '&#+$'   # from rfc2812
        
        self.buffer = ''
    
    #called when we get a result from the dns lookup
    def on_dns(self, result, error):
        if error:
            self.disconnect(error=error[1])
        else:
            #import os
            #import random
            #random.shuffle(result, os.urandom)
            if socket.has_ipv6: #prefer ipv6
                result = [(f, t, p, c, a) for (f, t, p, c, a) in result if f == socket.AF_INET6]+result
            elif hasattr(socket,"AF_INET6"): #ignore ipv6
                result = [(f, t, p, c, a) for (f, t, p, c, a) in result if f != socket.AF_INET6]
            
            self.failedlasthost = False
            
            for f, t, p, c, a in result:
                if (f, t, p, c, a) not in self.failedhosts:
                    try:
                        self.socket = socket.socket(f, t, p)
                        self.socket.settimeout(0)
                        self.socket.connect(a)
                    except socket.error, e:
                        if e[0] not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                            continue
                    self.source = ui.register_socket(self.socket, self.on_connect, self.on_readable, self.on_disconnect)
                    self.failedhosts.append((f, t, p, c, a))
                    if set(self.failedhosts) >= set(result):
                        self.failedlasthost = True
                    break
            else:
                self.failedlasthost = True
                if len(result):
                    self.failedhosts[:] = (f, t, p, c, a),
                    f, t, p, c, a = result[0]
                    try:
                        self.socket = socket.socket(f, t, p)
                        self.socket.settimeout(0)
                        self.socket.connect(a)
                        self.source = ui.register_socket(self.socket, self.on_connect, self.on_readable, self.on_disconnect)
                    except socket.error, e:
                        if e[0] not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                            self.disconnect(error="Couldn't find a host we can connect to")
                else:
                    self.disconnect(error="Couldn't find a host we can connect to")
    
    #called when the socket becomes open
    def on_connect(self):
        self.status = INITIALIZING
        self.failedhosts[:] = ()

        events.trigger('SocketConnect', events.data(network=self))
        
    #called when we can read from the socket
    def on_readable(self):
        try:
            reply = self.socket.recv(8192)
        except:
            import traceback
            traceback.print_exc()
        
        if reply:
            self.buffer = self.buffer + reply
            
            lines, self.buffer = self.buffer.rsplit("\r\n",1)
            
            for line in lines.split('\r\n'):
                if self.DEBUG:
                    print "<< %s" % line

                self.got_msg(line)
        else:
            err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err:
                self.disconnect(error=os.strerror(err))
            else:
                self.disconnect(error="Connection closed by remote host")
        
        return True
    
    def on_disconnect(self, errno, msg):
        if errno:
            self.disconnect(msg)
        else:
            self.disconnect()
    
    def raw(self, msg):
        if self.DEBUG:
            print ">> %s" % (msg + "\r\n").replace("\r\n", "\\r\\n")
        
        if self.status >= INITIALIZING:
            #have ui do the writing for us so we know all the data will be sent
            self.source.write(msg + "\r\n")
        
    def got_msg(self, msg):
        pmsg = parse_irc(msg, self.server)
    
        e_data = events.data(
                    msg=pmsg,
                    text=pmsg[-1],
                    network=self,
                    window=windows.get_default(self)
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
            
            self.source = ui.fork(self.on_dns, socket.getaddrinfo, self.server, self.port, 0, socket.SOCK_STREAM)
            
            events.trigger('Connecting', events.data(network=self))
    
    def disconnect(self, error=None):
        if self.socket:
            self.socket.close()
        
        if self.source:
            self.source.unregister()
            self.source = None
        
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
                        window=windows.get_default(self),
                        source=self.me,
                        newnick=self.nicks[0]
                        )
            events.trigger('Nick', e_data)
            self.me = self.nicks[0]
        
    def norm_case(self, string):
        return string.lower()
    
    def quit(self, msg=None):
        if self.status:
            try:
                if msg == None:
                    msg = conf.get('quitmsg', "%s - %s" % (urk.long_version, urk.website))
                self.raw("QUIT :%s" % msg)
            except:
                pass
            self.disconnect()
        
    def join(self, name, key=''):
        if key:
            key = ' '+key
        self.raw("JOIN %s%s" % (name,key))
        
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
                    window=windows.get_default(self)
                    )
        events.trigger('OwnText', e_data)

    def notice(self, target, msg):
        self.raw("NOTICE %s :%s" % (target, msg))
        
        e_data = events.data(
                    source=self.me,
                    target=str(target),
                    text=msg,
                    network=self,
                    window=windows.get_default(self)
                    )
        events.trigger('OwnNotice', e_data)


#this was ported from srvx's tools.c
def match_glob(text, glob, t=0, g=0):
    while g < len(glob):
        if glob[g] in '?*':
            star_p = q_cnt = 0
            while g < len(glob):
                if glob[g] == '*':
                    star_p = True
                elif glob[g] == '?':
                    q_cnt += 1
                else:
                    break
                g += 1
            t += q_cnt
            if t > len(text):
                return False
            if star_p:
                if g == len(glob):
                    return True
                for i in xrange(t, len(text)):
                    if text[i] == glob[g] and match_glob(text, glob, i+1, g+1):
                        return True
                return False
            else:
                if t == len(text) and g == len(glob):
                    return True
        if t == len(text) or g == len(glob) or text[t] != glob[g]:
            return False
        t += 1
        g += 1
    return t == len(text)
