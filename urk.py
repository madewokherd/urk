import events
import conf

if __name__ == "__main__":
    # FIXME, load an irc object ready to do our networked bidding

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
