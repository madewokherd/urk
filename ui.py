import time

import events

import pygtk
import gtk

import gobject

import conf

def connectToArlottOrg(widget):
    events.trigger("ConnectArlottOrg")
    
class UrkAbout(gtk.AboutDialog):
    def __init__(self, action):
        gtk.AboutDialog.__init__(self)
        
        self.set_name("Urk")
        self.set_version("8")
        self.set_copyright("Yes, 2004")
        self.set_comments("Comments")
        self.set_license("Gee Pee Ell")
        self.set_website("http://urk.sf.net")
        self.set_authors(["Marc","MadEwokHerd"])
        
        self.show_all()

def quit(action=None):
    enqueue(raise_keyboard_interrupt)

menu = (
    ("FileMenu", None, "_File"),
        ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, quit),
        ("Connect", None, "_Connect", None, None, connectToArlottOrg),
    
    ("EditMenu", None, "_Edit"),
        ("Preferences", gtk.STOCK_PREFERENCES, "Pr_eferences", None, None),
    
    ("HelpMenu", None, "_Help"),
        ("About", gtk.STOCK_ABOUT, "_About", None, None, UrkAbout)
)

ui_info = \
"""<ui>
 <menubar name="MenuBar">
  <menu action="FileMenu">
   <menuitem action="Connect"/>
   <menuitem action="Quit"/>
  </menu>
  
  <menu action="EditMenu">
   <menuitem action="Preferences"/>
  </menu>
  
  <menu action="HelpMenu">
   <menuitem action="About"/>
  </menu>
 </menubar>
</ui>"""



class IrcWindow(gtk.VBox):        
    # the all knowing print to our text window function
    def write(self, text):
        enqueue(self.write_unsafe, text)
    
    def write_unsafe(self, text):
        newline = "\n"
        
        v_buffer = self.view.get_buffer()
    
        if v_buffer.get_char_count() == 0:
            newline = ""
    
        v_buffer.insert(v_buffer.get_end_iter(),newline + text)
        
        if True: # i want this to be not scrolled up...
            self.view.scroll_mark_onscreen(self.mark)
    
    # we entered some text in the entry box
    def entered_text(self, entry, data=None):
        lines = entry.get_text().split("\n")

        for line in lines:
            if line:
                self.entered_line(line)
        
        entry.set_text("")
    
    def entered_line(self, text):
        e_data = events.data()
        e_data.window = self
        e_data.text = text
        e_data.network = self.get_data('network')
        events.trigger('Input', e_data)
        
    # top half of an irc window, channel window and nicklist                
    def top_section(self):
        self.view = gtk.TextView()
        self.view.set_wrap_mode(gtk.WRAP_WORD)
        self.view.set_editable(False)
        self.view.set_cursor_visible(False)
        
        #def blah(*args):
        #    print args
        
        #self.view.connect("move-cursor", blah)
        
        v_buffer = self.view.get_buffer()        
        self.mark = v_buffer.create_mark('end', v_buffer.get_end_iter(), False)

        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        win.add(self.view)

        return win
     
    # this is our editbox   
    def bottom_section(self):
        self.entry = gtk.Entry()
        self.entry.connect("activate", self.entered_text)

        return self.entry

    def __init__(self, title=None):
        gtk.VBox.__init__(self, False)
        
        self.title = title
        
        top, bot = self.top_section(), self.bottom_section()

        self.pack_start(top)
        self.pack_end(bot, expand=False)
        
        def focus_entry(*args):
            self.entry.grab_focus()

        self.connect("focus", focus_entry)
        
        def blah(*args):
            print args
        
        top.connect("focus", blah)
        
        self.show_all()
        
class IrcChannelWindow(IrcWindow):
    # top half of an irc window, channel window and nicklist                
    def top_section(self):
        self.nicklist = gtk.TreeView()
        
        win = gtk.HPaned()
        win.pack1(IrcWindow.top_section(self), resize=True)
        win.pack2(self.nicklist, resize=False)
        win.show_all()
        
        return win

class IrcUI(gtk.Window):
    def new_tab(self, window, network=None):
        enqueue(self.new_tab_unsafe, window, network=None)

    def new_tab_unsafe(self, window, network=None):
        title = gtk.Label(window.title)
        
        window.set_data('network', network)
        
        if network:
            n = self.tabs.get_n_pages()
            
            for i in reversed(xrange(n)):
                insert_candidate = self.tabs.get_nth_page(i)
                
                if insert_candidate.get_data('network') == network:
                    self.tabs.insert_page(window, title, i+1)
                    break
            else:
                self.tabs.append_page(window, title)
        else:
            self.tabs.append_page(window, title)
        
    def shutdown(self):
        conf.set("x", self.x)
        conf.set("y", self.y)
    
        conf.set("width", self.w)
        conf.set("height", self.h)

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        self.shutdown()
    
        enqueue(raise_quit)

    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        # create a new window
        gtk.Window.__init__(self)

        self.connect("delete_event", self.delete_event)
        self.connect("destroy", self.destroy)
        
        def record_resize(widget, event):
            self.w, self.h = self.get_size()
            self.x, self.y = self.get_position()

        self.connect("configure_event", record_resize)

        self.set_title("Urk")
        
        # FIXME reduce all of this to 1 line of code, or somehow make it
        #       neater

        self.x, self.y = conf.get("x"), conf.get("y")
        if self.x == None:
            self.x = -1

        if self.y == None:
            self.y = -1
            
        self.w = conf.get("width") or 500        
        self.h = conf.get("height") or 500            
            
        self.move(self.x, self.y)
        self.set_default_size(self.w, self.h)
        
        actions = gtk.ActionGroup("Actions")
        actions.add_actions(menu)
        
        ui = gtk.UIManager()
        ui.insert_action_group(actions, 0)
        
        try:
            mergeid = ui.add_ui_from_string(ui_info)
        except gobject.GError, msg:
            print "building menus failed: %s" % msg

        # create some tabs
        self.tabs = gtk.Notebook()
        
        self.tabs.set_border_width(10)                
        self.tabs.set_scrollable(True)
        self.tabs.set_show_border(True)
        
        def focus_entry(*args):
            initialWindow.entry.grab_focus()
        self.tabs.connect("focus", focus_entry)

        box = gtk.VBox(False)
        box.pack_start(ui.get_widget("/MenuBar"), expand=False)
        box.pack_end(self.tabs)
        
        initialWindow = IrcWindow("Status Window")

        self.new_tab(initialWindow)

        self.add(box)
        self.show_all()

queue = []
def enqueue(f, *args, **kwargs):
    queue.append((f, args, kwargs))

class Quitting(Exception):
    pass

def raise_quit():
    raise Quitting

def raise_keyboard_interrupt():
    raise KeyboardInterrupt

ui = IrcUI()

def start():
    try:
        while 1:
            gtk.main_iteration(block=False)
            while queue:
                f, args, kwargs = queue.pop()
                f(*args,**kwargs)
            time.sleep(.001)
    except KeyboardInterrupt:
        ui.shutdown()
    except Quitting:
        pass
