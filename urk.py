import events
import conf

import pygtk
import gtk

class IrcWindow(gtk.VBox):        
    # top half of an irc window, channel window and nicklist                
    def top_section(self):
        self.view = gtk.TextView()
        self.view.set_wrap_mode(gtk.WRAP_WORD)
        self.view.set_editable(False)
        self.view.set_cursor_visible(False)
        self.view.show()

        self.text = self.view.get_buffer()
        
        scrwin = gtk.ScrolledWindow()
        scrwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrwin.add(self.view)
        scrwin.show()
        
        return scrwin
     
    # this is our editbox   
    def bottom_section(self):
        textEntry = gtk.Entry()
        
        textEntry.show()
        
        return textEntry

    def __init__(self, title=None):
        gtk.VBox.__init__(self, False)
        
        self.title = title

        self.pack_start(self.top_section())
        self.pack_end(self.bottom_section(), expand=False)
        
        self.show()
        
class IrcChannelWindow(IrcWindow):
    # top half of an irc window, channel window and nicklist                
    def top_section(self):
        self.nicklist = gtk.TreeView()
        self.nicklist.show()
        
        win = gtk.HPaned()
        win.pack1(IrcWindow.top_section(self), resize=True)
        win.pack2(self.nicklist, resize=False)
        win.show()
        
        return win

class IrcUI:
    def newTab(self, window):
        title = gtk.Label(window.title)
         
        self.tabs.append_page(window, title)

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def __init__(self):
        # create a new window
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        window.connect("delete_event", self.delete_event)
        window.connect("destroy", self.destroy)

        window.set_border_width(10)
        window.set_title("Irc")
        window.resize(500, 500) 
        
        # create some tabs
        self.tabs = gtk.Notebook()
                
        self.tabs.set_scrollable(True)
        self.tabs.set_show_border(True)

        self.newTab(IrcWindow("Status Window"))

        window.add(self.tabs)
        
        self.tabs.show()
        window.show()       

def main():
    IrcUI()
    
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
    
    gtk.main()
    
if __name__ == "__main__":
    main()
