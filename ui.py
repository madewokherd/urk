import time
import thread
import traceback

import gobject
import gtk
import pango

import __main__ as urk
import irc
import conf
import events
import parse_mirc
          
MOD_MASK = 0
for m in (gtk.gdk.CONTROL_MASK, gtk.gdk.MOD1_MASK, gtk.gdk.MOD3_MASK,
             gtk.gdk.MOD4_MASK, gtk.gdk.MOD5_MASK):
    MOD_MASK |= m   

HILIT = 4
TEXT = 2
EVENT = 1

COLOR = {
    HILIT: "yellow",
    TEXT: "red",
    EVENT: "#555"
    }

#this is how we put lots of related ugliness in one place so we don't have to
#look at it all the time

main_thread = thread.get_ident()

class reference(object):
    __slots__ = ['value']

class pygtk_lookup_class(object):
    __slots__ = ['f']
    
    def __init__(self, f):
        self.f = f
    
    def __call__(self, *args, **kwargs):
        if main_thread == thread.get_ident():
            return self.f(*args, **kwargs)
        else:
            result = reference()
            mutex = thread.allocate_lock()
            mutex.acquire()
            def do_in_main_thread():
                result.value = self.f(*args, **kwargs)
                mutex.release()
            enqueue(do_in_main_thread)
            mutex.acquire()
            return result.value

class pygtk_descriptor_lookup_class(pygtk_lookup_class):
    def __get__(self, instance, owner):
        return pygtk_lookup(self.f.__get__(instance, owner))
    
    def __set__(self, instance, owner):
        self.f.__set__(instance, owner)

    def __delete__(self, instance, owner):
        self.f.__delete__(instance, owner)

class pygtk_procedure_class(object):
    __slots__ = ['f']
    
    def __init__(self, f):
        self.f = f
    
    def __call__(self, *args, **kwargs):
        if main_thread == thread.get_ident():
            self.f(*args, **kwargs)
        else:
            enqueue(self.f, *args, **kwargs)

class pygtk_descriptor_procedure_class(pygtk_procedure_class):
    def __get__(self, instance, owner):
        return pygtk_procedure(self.f.__get__(instance, owner))
    
    def __set__(self, instance, owner):
        self.f.__set__(instance, owner)

    def __delete__(self, instance, owner):
        self.f.__delete__(instance, owner)

def pygtk_lookup(f):
    if hasattr(f, '__get__'):
        return pygtk_descriptor_lookup_class(f)
    else:
        return pygtk_lookup_class(f)

def pygtk_procedure(f):
    if hasattr(f, '__get__'):
        return pygtk_descriptor_procedure_class(f)
    else:
        return pygtk_procedure_class(f)

def urk_about(action):
    about = gtk.AboutDialog()
    
    about.set_name("Urk")
    about.set_version("0.-1.2")
    about.set_copyright("Copyright \xc2\xa9 2005 Vincent Povirk, Marc Liddell")
    about.set_website("http://urk.sf.net/")
    about.set_authors(["Vincent Povirk", "Marc Liddell"])
    
    about.show_all()
    
def get_tab_actions(page_num):
    def close_tab(action):
        window = window_list.get_nth_page(page_num)
        close_window(window)
        
    to_add = (
        ("CloseTab", gtk.STOCK_CLOSE, "_Close Tab", None, None, close_tab),
        )
        
    tab_actions = gtk.ActionGroup("Tab")
    tab_actions.add_actions(to_add)
    
    return tab_actions
    
def get_urk_actions(ui):
    def connectToArlottOrg(widget):
        events.trigger("ConnectArlottOrg")

    to_add = (
        ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, ui.shutdown),
            ("Connect", None, "_Connect", "<control>S", None, connectToArlottOrg),
        
        ("EditMenu", None, "_Edit"),
            ("Preferences", gtk.STOCK_PREFERENCES, "Pr_eferences", "<control>P", None),
        
        ("HelpMenu", None, "_Help"),
            ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about)
        )
    
    urk_actions = gtk.ActionGroup("Urk")   
    urk_actions.add_actions(to_add)
    
    return urk_actions

# Label used to display/edit your current nick on a network
class NickLabel(gtk.EventBox):
    mode = "show"
    
    def set_nick(self, nick):
        self.label.set_text(nick)
        self.edit.set_text(nick)
    
    def show_nick(self, *args):
        if self.mode == "edit":
            self.mode = "show"
        
            self.remove(self.edit)
            self.add(self.label)
            
            self.entry.grab_focus()

    def edit_nick(self, *args):
        if self.mode == "show":
            self.mode = "edit"
            
            self.edit.set_text(self.label.get_text())
        
            self.remove(self.label)
            self.add(self.edit)
            
            self.edit.grab_focus()

    def __init__(self, entry, nick, nick_change):
        gtk.EventBox.__init__(self)

        self.label = gtk.Label(nick)
        self.label.set_padding(5, 0)
        self.add(self.label)
        
        self.edit = gtk.Entry()
        self.edit.set_text(nick)
        self.edit.show()
        
        self.entry = entry

        def change_nick(*args):
            if self.mode == "edit":
                oldnick, newnick = self.label.get_text(), self.edit.get_text()
            
                if newnick and newnick != oldnick:
                    nick_change(newnick)

                self.show_nick()
                
        self.edit.connect("activate", change_nick)

        self.connect("button-press-event", self.edit_nick)
        self.edit.connect("focus-out-event", self.show_nick)

# The entry which you type in to send messages        
class EntryBox(gtk.Entry):
    win = None
    history = []

    # Generates an input event
    def entered_text(self, *args):
        lines = self.get_text().split("\n")

        for line in lines:
            if line:
                e_data = events.data()
                e_data.window = self.win
                e_data.text = line
                e_data.network = self.win.network
                events.trigger('Input', e_data)
                
                self.history.insert(1, line)
                self.history_i = 0
    
        self.set_text("")
    
    # Explores the history of this entry box
    #  0 means most recent which is what you're currently typing
    #  anything greater means things you've typed and sent    
    def history_explore(self, di): # assume we're going forward in history 
        if di == 1:
            # we're going back in history
            
            # when we travel back in time, we need to remember
            # where we were, so we can go back to the future
            if self.history_i == 0 and self.get_text():
                self.history.insert(1, self.get_text())
                self.history_i = 1

        if self.history_i + di in range(len(self.history)):
            self.history_i += di

        self.set_text(self.history[self.history_i])
        self.set_position(-1)

    def __init__(self, window):
        gtk.Entry.__init__(self)
        
        self.win = window

        self.connect("activate", self.entered_text)
   
        self.history = [""]
        self.history_i = 0
        
        def check_history_explore(widget, event):
            up = gtk.gdk.keyval_from_name("Up")
            down = gtk.gdk.keyval_from_name("Down")
            
            if event.keyval == up:
                self.history_explore(1)
                return True
                
            elif event.keyval == down:
                self.history_explore(-1)
                return True

        self.connect("key-press-event", check_history_explore)
        
class IrcTabLabel(gtk.EventBox):
    def update(self):
        activity, title = self.child_window.activity, self.child_window.title
        
        if activity & HILIT:
            text = "<span foreground='%s'>%s</span>" % (COLOR[HILIT], title)
        elif activity & TEXT:
            text = "<span foreground='%s'>%s</span>" % (COLOR[TEXT], title)
        elif activity & EVENT:
            text = "<span foreground='%s'>%s</span>" % (COLOR[EVENT], title)
        else:
            text = "<span>%s</span>" % title
            
        self.label.set_markup(text)

    def tab_popup(self, widget, event):
        if event.button == 3: # right click
            page_num = window_list.page_num(widget.child_window)
            
            # add some tab UI                
            tab_id = ui_manager.add_ui_from_file("tabui.xml")
            ui_manager.insert_action_group(get_tab_actions(page_num), 0)

            tab_menu = ui_manager.get_widget("/TabPopup")
            
            # remove the tab UI, so we can recompute it later
            def remove_tab_ui(action):
                ui_manager.remove_ui(tab_id)
            tab_menu.connect("deactivate", remove_tab_ui)

            tab_menu.popup(None, None, None, event.button, event.time)

    def __init__(self, window):
        gtk.EventBox.__init__(self)

        self.child_window = window
        self.connect("button-press-event", self.tab_popup)
        
        self.label = gtk.Label()        
        self.update()
        self.add(self.label)
        
        self.show_all()

class IrcWindow(gtk.VBox):
    # the unknowing print weird things to our text window function
    @pygtk_procedure
    def write(self, text, activity_type=EVENT):
        tag_data, text = parse_mirc.parse_mirc(text)
    
        buffer = self.view.get_buffer()
        
        old_end = buffer.get_end_iter()
        
        end_rect = self.view.get_iter_location(old_end)
        vis_rect = self.view.get_visible_rect()

        do_scroll = end_rect.y + end_rect.height <= vis_rect.y + vis_rect.height

        char_count = buffer.get_char_count()

        buffer.insert(old_end, text + "\n")

        if window_list.get_nth_page(window_list.get_current_page()) != self:
            self.activity |= activity_type
            self.label.update()

        for props, start_i, end_i in tag_data:
            start_pos = buffer.get_iter_at_offset(start_i + char_count)
            end_pos = buffer.get_iter_at_offset(end_i + char_count)

            for i, (prop, val) in enumerate(props):
                if val == parse_mirc.BOLD:
                    props[i] = prop, pango.WEIGHT_BOLD

                elif val == parse_mirc.UNDERLINE:
                   props[i] = prop, pango.UNDERLINE_SINGLE
                
            tag_name = str(hash(tuple(props)))
                 
            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **dict(props))
                
            buffer.apply_tag_by_name(tag_name, start_pos, end_pos)

        if do_scroll:        
            def scroll():
                new_end = buffer.get_end_iter()
                self.view.scroll_mark_onscreen(buffer.create_mark("", new_end))
                
            enqueue(scroll)

    # this is our text entry widget
    def entry_box(self):
        self.entry = EntryBox(self)
        
        # FIXME: please make this whatever you need to do to change nick
        def nick_change(newnick):
            e_data = events.data()
            e_data.window = self
            e_data.text = "/nick %s" % newnick
            e_data.network = self.network
            events.trigger('Input', e_data)
            
        if self.network:
            if self.network.connected:
                nick = self.network.me
            else:
                nick = self.network.nicks[0]
        else:
            nick = conf.get("nick") or "MrUrk"
        
        self.nick_label = NickLabel(self.entry, nick, nick_change)

        box = gtk.HBox()
        box.pack_start(self.entry)
        box.pack_end(self.nick_label, expand=False)

        return box
        
    # non-channel channel window, no nicklist         
    def chat_view(self):
        self.view = gtk.TextView(gtk.TextBuffer(tag_table))
        
        self.view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.view.set_editable(False)
        self.view.set_cursor_visible(False)
        
        self.view.set_property("left-margin", 3)
        self.view.set_property("right-margin", 3)
        self.view.set_property("indent", 0)

        def transfer_text(widget, event):
            modifiers_on = event.state & MOD_MASK

            if event.string and not modifiers_on:
                self.entry.grab_focus()
                self.entry.insert_text(event.string, -1)
                self.entry.set_position(-1)
        
        self.view.connect("key-press-event", transfer_text)
        
        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        win.set_border_width(2)
        win.add(self.view)

        return win
    
    def __init__(self, network, type, id, title=None):
        gtk.VBox.__init__(self, False)
        
        if network:
            id = network.normalize_case(id)
        
        self.network = network
        self.type = type
        self.id = id

        self.title = title or id
        self.activity = 0
        
        self.label = IrcTabLabel(self)
        
        cv, eb = self.chat_view(), self.entry_box()

        self.pack_start(cv)
        self.pack_end(eb, expand=False)
  
        self.show_all()

class IrcChannelWindow(IrcWindow):
    # channel window and nicklist               
    def chat_view(self):
        self.nicklist = gtk.ListStore(str)
        
        cv = IrcWindow.chat_view(self)
        
        tv = gtk.TreeView(self.nicklist)
        tv.insert_column_with_attributes(
            0, self.title, gtk.CellRendererText(), text=0
            )
        
        win = gtk.HPaned()
        win.pack1(cv, resize=True)
        win.pack2(tv, resize=True)

        return win
        
    def set_nicklist(self, nicks):
        self.nicklist.clear()
        
        for nick in nicks:
            self.nicklist.append([nick])
        
class IrcTabs(gtk.Notebook):
    def __init__(self):
        gtk.Notebook.__init__(self)
        
        self.window_list = {}
        
        if conf.get("ui-gtk/tab-pos") is not None:
            self.set_property("tab-pos", conf.get("ui-gtk/tab-pos"))
        else:
            self.set_property("tab-pos", gtk.POS_TOP)

        if conf.get("ui-gtk/tab-margin") is not None:
            self.set_border_width(conf.get("ui-gtk/tab-margin"))
        else:
            self.set_border_width(10)
   
        self.set_scrollable(True)
        self.set_show_border(True)
        
        def focus_entry(self, window, page_num):
            window = self.get_nth_page(page_num)
        
            window.activity = 0
            window.label.update()
            
            enqueue(window.entry.grab_focus)
        
            events.trigger("Active", window)
        
        self.connect_after("switch-page", focus_entry)
        
    def __setitem__(self, item, value):
        network, type, id = item
        
        if network:
            id = network.normalize_case(id)
    
        self.window_list[network, type, id] = value
 
    def __getitem__(self, item):
        network, type, id = item
        
        if network:
            id = network.normalize_case(id)

        if (network, type, id) in self.window_list:
            return self.window_list[network, type, id]
            
    def __delitem__(self, item):
        network, type, id = item
        
        if network:
            id = network.normalize_case(id)

        events.trigger("Close", self.window_list[network, type, id])
        self.remove_page(self.page_num(self.window_list[network, type, id]))
        del self.window_list[network, type, id]

    def __iter__(self):
        return iter(self.window_list)
        
    def __len__(self):
        return len(self.window_list)

class IrcUI(gtk.Window):
    def shutdown(self, *args):
        conf.set("xy", self.get_position())
        conf.set("wh", self.get_size())

        if gtk.main_level():
            gtk.main_quit()

    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        self.set_title("Urk")

        # layout
        xy = conf.get("xy") or (-1, -1)
        wh = conf.get("wh") or (500, 500)

        self.move(*xy)
        self.set_default_size(*wh)
        
        self.add_accel_group(ui_manager.get_accel_group())
        ui_manager.add_ui_from_file("ui.xml")
        ui_manager.insert_action_group(get_urk_actions(self), 0)
        
        menu = ui_manager.get_widget("/MenuBar")

        # widgets
        box = gtk.VBox(False)
        box.pack_start(menu, expand=False)
        box.pack_end(window_list)
        
        self.connect("delete_event", self.shutdown)

        self.add(box)
        self.show_all()

# Select the page with the given window or with the given tab position
@pygtk_procedure
def activate(window):
    # if this is an actual window, then we want its tab number
    if not isinstance(window, int):
        window = window_list.page_num(window)

    window_list.set_current_page(window)
    window_list.get_nth_page(window).entry.grab_focus()

# Always make a new window and return it.
@pygtk_lookup
def force_make_window(network, type, nid, title, is_chan):
    if is_chan:
        window = IrcChannelWindow(network, type, nid, title=title)
    else:
        window = IrcWindow(network, type, nid, title=title)
        
    window.network = network

    pos = len(window_list)
    if network:
        for i in reversed(range(pos)):
            if window_list.get_nth_page(i).network == window.network:
                pos = i+1
                break

    window_list[network, type, nid] = window
    window_list.insert_page(window, None, pos)
    window_list.set_tab_label(window, window.label)

    return window

# Make a window for the given network, type, id if it doesn't exist.
#  Return it.
def make_window(network, type, id, title=None, is_chan=False):
    if window_list[network, type, id]:
        return window_list[network, type, id]
        
    else:
        return force_make_window(network, type, id, title or id, is_chan)

# Close a window.
def close_window(window):
    del window_list[window.network, window.type, window.id]

queue = []
def enqueue(f, *args, **kwargs):
    queue.append((f, args, kwargs))

def process_queue():
    try:
        if queue:
            f, args, kwargs = queue.pop(0)
            try:
                f(*args,**kwargs)
            except:
                traceback.print_exc()
        else:
            time.sleep(0.001)
        return True
    except KeyboardInterrupt:
        ui.shutdown()
        
def start():
    if not window_list:
        urk.connect(irc.Network("irc.flugurgle.org"))

    gobject.idle_add(process_queue)
    gtk.main()

# This holds all tags for all windows ever    
tag_table = gtk.TextTagTable()

# UI manager to use throughout   
ui_manager = gtk.UIManager()
    
# build our tab widget
window_list = IrcTabs()

# build our overall UI
ui = IrcUI()
