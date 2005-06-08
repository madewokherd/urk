import events
import conf

if __name__ == "__main__":
    import irc
    #irc.DEBUG = True
    
    #x = irc.Network("irc.arlott.org", "Marc", "irc.arlott.org")
    #x.connect()

    # FIXME, look in our conf
    #        what have we got?
    #        any scripts to load?
    #        load 'em up, register their functions
    
    events.load("script.py")
    events.trigger("Start")

    # FIXME, maybe one of our scripts asked us to connect to something
    #        or open some random window for something
    #        or print to the screen, we should do that
    
    import ui
