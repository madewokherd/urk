import events

import pygtk
import gtk

class IrcWindow(gtk.VBox):        
    # the all knowing print to our text window function
    def write(self, text):
        newline = "\n"
    
        if self.text.get_char_count() == 0:
            newline = ""
    
        self.text.insert(self.text.get_end_iter(),newline + text)
        
        if True: # i want this to be not scrolled up...
            self.view.scroll_mark_onscreen(self.mark)
    
    # we entered some text in the entry box
    def entered_text(self, entry, event, data=None):
        if event.keyval == gtk.gdk.keyval_from_name("Return"):
            lines = entry.get_text().split("\n")

            for line in lines:
                if line:
                    self.entered_line(line)
            
            entry.set_text("")
    
    def entered_line(self, text):
        events.trigger('Input', events.data(window=self, text=text))
        
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
        
        self.mark = self.text.create_mark('end', self.text.get_end_iter(), False)
        
        return scrwin
     
    # this is our editbox   
    def bottom_section(self):
        self.entry = gtk.Entry()
        
        self.entry.connect("key_press_event", self.entered_text)
        
        self.entry.show()
        
        return self.entry

    def focus(self, widget, event):
        self.entry.grab_focus()

    def __init__(self, title=None):
        gtk.VBox.__init__(self, False)
        
        self.title = title

        self.pack_start(self.top_section())
        self.pack_end(self.bottom_section(), expand=False)
        
        self.set_focus_child(self.entry)
        
        self.connect('focus', self.focus)
        
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
        # threading stuff
        gtk.gdk.threads_init()
        
        # create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)

        self.window.set_border_width(10)
        self.window.set_title("Irc")
        self.window.resize(500, 500) 
        
        # create some tabs
        self.tabs = gtk.Notebook()
                
        self.tabs.set_scrollable(True)
        self.tabs.set_show_border(True)

        initialWindow = IrcWindow("Status Window")

        self.newTab(initialWindow)

        #self.newTab(IrcWindow("Extra Window"))

        self.window.add(self.tabs)
        
        self.tabs.show()
        
        self.window.show()
        
        self.tabs.set_focus_child(initialWindow)
        
IrcUI()
gtk.main()
