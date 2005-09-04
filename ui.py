import gobject
import gtk
import pango

import irc
import conf
import events
import parse_mirc

# IO Type Constants
IO_IN = gobject.IO_IN
IO_OUT = gobject.IO_OUT
IO_PRI = gobject.IO_PRI
IO_ERR = gobject.IO_ERR
IO_HUP = gobject.IO_HUP

# Priority Constants
PRIORITY_HIGH = gobject.PRIORITY_HIGH
PRIORITY_DEFAULT = gobject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = gobject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = gobject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = gobject.PRIORITY_LOW

def register_io(f, fd, condition, priority=PRIORITY_DEFAULT_IDLE, *args, **kwargs):
    def callback(source, cb_condition):
        return f(*args, **kwargs)
    return gobject.io_add_watch(fd, condition, callback, priority=priority)

def register_idle(f, priority=PRIORITY_DEFAULT_IDLE, *args, **kwargs):
    def callback():
        return f(*args, **kwargs)
    return gobject.idle_add(callback, priority=priority)

def register_timer(time, f, priority=PRIORITY_DEFAULT_IDLE, *args, **kwargs):
    def callback():
        return f(*args, **kwargs)
    return gobject.timeout_add(time, callback, priority=priority)

def unregister(tag):
    gobject.source_remove(tag)

# Window activity Constants
HILIT = 4
TEXT = 2
EVENT = 1

def urk_about(action):
    import __main__
    
    about = gtk.AboutDialog()
    
    about.set_name(__main__.name+" (GTK+ Frontend)")
    about.set_version(".".join(str(x) for x in __main__.version))
    about.set_copyright("Copyright \xc2\xa9 %s" % __main__.copyright)
    about.set_website(__main__.website)
    about.set_authors(__main__.authors)
    
    about.show_all()
    
def get_tab_actions(window):
    def close_tab(action):
        window.close()
        
    to_add = (
        ("CloseTab", gtk.STOCK_CLOSE, "_Close Tab", None, None, close_tab),
        )
        
    tab_actions = gtk.ActionGroup("Tab")
    tab_actions.add_actions(to_add)
    
    return tab_actions
    
def get_urk_actions(ui):
    to_add = (
        ("FileMenu", None, "_File"),
            ("Quit", gtk.STOCK_QUIT, "_Quit", "<control>Q", None, gtk.main_quit),
        
        ("HelpMenu", None, "_Help"),
            ("About", gtk.STOCK_ABOUT, "_About", None, None, urk_about)
        )
    
    urk_actions = gtk.ActionGroup("Urk")   
    urk_actions.add_actions(to_add)
    
    return urk_actions
    
class Nicklist(gtk.VBox):
    def __init__(self, window):
        gtk.VBox.__init__(self)
        
        self.userlist = gtk.ListStore(str)
        
        view = gtk.TreeView(self.userlist)
        view.set_size_request(0, -1)
        view.set_headers_visible(False)

        view.insert_column_with_attributes(
            0, "", gtk.CellRendererText(), text=0
            )
            
        view.get_column(0).set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        view.set_property("fixed-height-mode", True)
        
        view.set_style(get_style("nicklist"))
        
        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)   
        win.add(view)

        self.pack_end(win)

# Label used to display/edit your current nick on a network
class NickEdit(gtk.EventBox):
    def update(self):
        self.label.set_text(self.win.network.me)
        self.edit.set_text(self.win.network.me)
    
    def toggle(self, *args):
        if self.mode == "edit":
            self.mode = "show"
        
            self.remove(self.edit)
            self.add(self.label)
            
            self.win.input.grab_focus()

        else:
            self.mode = "edit"
            
            self.edit.set_text(self.label.get_text())
        
            self.remove(self.label)
            self.add(self.edit)
            
            self.edit.grab_focus()

    def __init__(self, window):
        gtk.EventBox.__init__(self)
        
        self.mode = "show"
        self.win = window

        self.label = gtk.Label()
        self.label.set_padding(5, 0)
        self.add(self.label)
        
        self.edit = gtk.Entry()
        self.edit.show()

        def nick_change(*args):
            oldnick, newnick = self.label.get_text(), self.edit.get_text()
        
            if newnick and newnick != oldnick:
                events.run_command('nick %s' % newnick, self.win, self.win.network)

            self.win.input.grab_focus()
                
        self.edit.connect("activate", nick_change)

        self.connect("button-press-event", self.toggle)
        self.edit.connect("focus-out-event", self.toggle)
        
        self.update()

# The entry which you type in to send messages        
class TextInput(gtk.Entry):
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
                
                if not e_data.done:
                    events.run_command(line, self.win, self.win.network)
                
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
        
        up = gtk.gdk.keyval_from_name("Up")
        down = gtk.gdk.keyval_from_name("Down")        
        def check_history_explore(widget, event):
            if event.keyval == up:
                self.history_explore(1)
                return True
                
            elif event.keyval == down:
                self.history_explore(-1)
                return True

        self.connect("key-press-event", check_history_explore)
        
class TextOutput(gtk.TextView):
    # the unknowing print weird things to our text widget function
    def write(self, text, activity_type=EVENT):
        tag_data, text = parse_mirc.parse_mirc(text)
    
        buffer = self.get_buffer()
        
        cc = buffer.get_char_count()
        end = buffer.get_end_iter()
        
        end_rect = self.get_iter_location(end)
        vis_rect = self.get_visible_rect()
        
        # this means we're scrolled down right to the bottom
        # we interpret this to mean we should scroll down after we've
        # inserted more text into the buffer
        if end_rect.y + end_rect.height <= vis_rect.y + vis_rect.height:
            def scroll():
                self.scroll_mark_onscreen(buffer.get_mark("end"))
                
            register_idle(scroll)

        buffer.insert(end, text + "\n")

        for tag_props, start_i, end_i in tag_data:
            for i, (prop, val) in enumerate(tag_props):
                if val == parse_mirc.BOLD:
                    tag_props[i] = prop, pango.WEIGHT_BOLD

                elif val == parse_mirc.UNDERLINE:
                    tag_props[i] = prop, pango.UNDERLINE_SINGLE
                
            tag_name = str(hash(tuple(tag_props)))
                 
            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **dict(tag_props))
                
            buffer.apply_tag_by_name(
                tag_name, 
                buffer.get_iter_at_offset(start_i + cc),
                buffer.get_iter_at_offset(end_i + cc)
                )

    def __init__(self, window):
        gtk.TextView.__init__(self, gtk.TextBuffer(tag_table))
        
        buffer = self.get_buffer()        
        buffer.create_mark("end", buffer.get_end_iter(), False)
        
        self.win = window
        
        self.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.set_editable(False)
        self.set_cursor_visible(False)
        
        self.set_property("left-margin", 3)
        self.set_property("right-margin", 3)
        self.set_property("indent", 0)
        
        self.set_style(get_style("view"))

class WindowLabel(gtk.EventBox):
    def update(self):
        activity_markup = {
            HILIT: "<span style='italic' foreground='#00F'>%s</span>",
            TEXT: "<span foreground='red'>%s</span>",
            EVENT: "<span foreground='#363'>%s</span>",
            }
    
        for a_type in (HILIT, TEXT, EVENT):
            if self.win.activity & a_type:
                title = activity_markup[a_type] % self.win.title
                break
        else:
            title = self.win.title
            
        self.label.set_markup(title)

    def tab_popup(self, widget, event):
        if event.button == 3: # right click
            # add some tab UI                
            tab_id = ui_manager.add_ui_from_file("tabui.xml")
            ui_manager.insert_action_group(get_tab_actions(self.win), 0)

            tab_menu = ui_manager.get_widget("/TabPopup")
            
            # remove the tab UI, so we can recompute it later
            def remove_tab_ui(action):
                ui_manager.remove_ui(tab_id)
            tab_menu.connect("deactivate", remove_tab_ui)

            tab_menu.popup(None, None, None, event.button, event.time)

    def __init__(self, window):
        gtk.EventBox.__init__(self)

        self.win = window
        self.connect("button-press-event", self.tab_popup)
        
        self.label = gtk.Label()        
        self.add(self.label)
        
        self.update()
        
class Window(gtk.VBox):
    def get_title(self):
        return self.__title
    
    def set_title(self, value):
        self.__title = value
        self.label.update()
    
    title = property(get_title, set_title)
    
    def get_activity(self):
        return self.__activity
    
    def set_activity(self, value):
        self.__activity = value
        self.label.update()
        
    activity = property(get_activity, set_activity)
    
    def activate(self):
        window_list.nb.set_current_page(window_list.nb.page_num(self))
    
    def close(self):
        events.trigger("Close", self)
        del window_list[self.network, self.type, self.id]
    
    def __init__(self, network, type, id, title=None):
        gtk.VBox.__init__(self, False)

        if network:
            id = network.normalize_case(id)
        
        self.network = network
        self.type = type
        self.id = id
        
        self.__title = title or id
        self.__activity = 0
        
        self.label = WindowLabel(self)
        self.label.show_all()
        
        MOD_MASK = 0
        for m in (gtk.gdk.CONTROL_MASK, gtk.gdk.MOD1_MASK, gtk.gdk.MOD3_MASK,
                        gtk.gdk.MOD4_MASK, gtk.gdk.MOD5_MASK):
            MOD_MASK |= m   

        def transfer_text(widget, event):
            modifiers_on = event.state & MOD_MASK

            if event.string and not modifiers_on:
                self.input.grab_focus()
                self.input.insert_text(event.string, -1)
                self.input.set_position(-1)
        
        self.connect("key-press-event", transfer_text)

def ServerWindow(network, type, id, title=None):
    w = window_list[network, type, id]

    if not w:
        w = Window(network, type, id, title or id)

        def write(text, activity_type=EVENT):
            if get_active() != w:
                w.activity |= activity_type
        
            w.output.write(text, activity_type)
        w.write = write

        w.output = TextOutput(w)
        w.input = TextInput(w)
        
        w.nick_label = NickEdit(w)
        
        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(w.output)
        
        w.pack_start(topbox)
        
        botbox = gtk.HBox()
        botbox.pack_start(w.input)
        botbox.pack_end(w.nick_label, expand=False)
        
        w.pack_end(botbox, expand=False)

        w.show_all()
        
        window_list[network, type, id] = w
    
    return w
    
QueryWindow = ServerWindow

def ChannelWindow(network, type, id, title=None):
    w = window_list[network, type, id]

    if not w:
        w = Window(network, type, id, title or id)
        
        def write(text, activity_type=EVENT):
            if get_active() != w:
                w.activity |= activity_type
        
            w.output.write(text, activity_type)
        w.write = write

        def set_nicklist(nicks):
            w.nicklist.userlist.clear()
            
            for nick in nicks:
                w.nicklist.userlist.append([nick])
        w.set_nicklist = set_nicklist

        w.output = TextOutput(w)
        w.input = TextInput(w)
        
        w.nicklist = Nicklist(w)
        
        w.nick_label = NickEdit(w)

        topbox = gtk.ScrolledWindow()
        topbox.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        topbox.add(w.output)
        
        pane = gtk.HPaned()
        pane.pack1(topbox, resize=True, shrink=False)
        pane.pack2(w.nicklist, resize=False, shrink=True)

        def set_pane_pos():
            pos = conf.get("ui-gtk/nicklist-width")
            if pos is not None:
                pos = pane.get_property("max-position") - conf.get("ui-gtk/nicklist-width")
            else:
                pos = pane.get_property("max-position")
        
            pane.set_position(pos)
        register_idle(set_pane_pos)

        def connect_save():
            def save_nicklist_width(pane, event):
                pos = pane.get_property("max-position") - pane.get_position()

                conf.set("ui-gtk/nicklist-width", pos)
        
            pane.connect("size-request", save_nicklist_width)
        register_idle(connect_save)

        botbox = gtk.HBox()
        botbox.pack_start(w.input)
        botbox.pack_end(w.nick_label, expand=False)
        
        w.pack_start(pane)        
        w.pack_end(botbox, expand=False)

        w.show_all()
        
        window_list[network, type, id] = w
    
    return w
  
class Tabs(dict):       
    def __getitem__(self, item):
        network, type, id = item
        
        if network:
            id = network.normalize_case(id)

        if (network, type, id) in self:
            return dict.__getitem__(self, (network, type, id))

    def __setitem__(self, nti, window):
        network, type, id = nti
        
        if network:
            id = network.normalize_case(id)
        
        pos = len(self)
        if window.network:
            for i in reversed(range(pos)):
                if self.nb.get_nth_page(i).network == window.network:
                    pos = i+1
                    break
                    
        dict.__setitem__(self, (network, type, id), window)
                    
        self.nb.insert_page(window, None, pos)
        self.nb.set_tab_label(window, window.label)

    def __delitem__(self, item):
        network, type, id = item
        
        if network:
            id = network.normalize_case(id)

        self.nb.remove_page(self.nb.page_num(self[network, type, id]))
        dict.__delitem__(self, (network, type, id))
        
    def __init__(self):
        dict.__init__(self)
        
        self.nb = gtk.Notebook()
        
        tab_pos = conf.get("ui-gtk/tab-pos")
        if tab_pos is not None:
            self.nb.set_property("tab-pos", tab_pos)
        else:
            self.nb.set_property("tab-pos", gtk.POS_TOP)

        self.nb.set_border_width(10)
        self.nb.set_scrollable(True)
        self.nb.set_show_border(True)
        
        def focus_input(nb, wptr, page_num):
            window = nb.get_nth_page(page_num)
        
            window.activity = 0
            
            register_idle(window.input.grab_focus)
        
            events.trigger("Active", window)
            
        self.nb.connect("switch-page", focus_input)

class UrkUI(gtk.Window):
    def __init__(self):
        # threading stuff
        gtk.gdk.threads_init()
        
        gtk.Window.__init__(self)
        self.set_title("Urk")
        
        def save_xywh(*args):
            conf.set("xy", self.get_position())
            conf.set("wh", self.get_size())
        self.connect("configure_event", save_xywh)
        self.connect("delete_event", gtk.main_quit)

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
        box.pack_end(window_list.nb)

        self.add(box)
        self.show_all()
        
def get_window_for(network=None, type=None, id=None):
    if network and id:
        id = network.normalize_case(id)

    for n, t, i in list(window_list):
        if network and n != network:
            continue
        if type and t != type:
            continue
        if id and i != id:
            continue
            
        yield window_list[n, t, i]
        
def get_status_window(network):
    for n, t, i in window_list:
        if t == "status" and n == network:
            return window_list[n, t, i]
        
def get_active():
    active = window_list.nb.get_current_page()
    return window_list.nb.get_nth_page(active)

def start():
    if not window_list:
        first_network = irc.Network("irc.flugurgle.org")
        
        ChannelWindow(
            first_network, 
            "status", 
            "Status Window", 
            "[%s]" % first_network.server
            )

        #ServerWindow(
        #    first_network, 
        #    "batus", 
        #    "Status Window", 
        #    "[%s]" % first_network.server
        #    )
        
        #first_window.set_nicklist(str(x) for x in range(100))
        
    #for i in range(1000):
    #    first_window.write("\x040000CC<\x04nick\x040000CC>\x04 text")
    #register_idle(ui.shutdown)

    try:
        gtk.main()
    except KeyboardInterrupt:
        pass

#FIXME: MEH hates dictionaries, they remind him of the bad words
styles = {}
    
def get_style(widget):
    if widget in styles:
        return styles[widget]

def set_style(widget, style):
    def apply_style_fg(wdg, value):
        wdg.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

    def apply_style_bg(wdg, value):
        wdg.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

    def apply_style_font(wdg, value):
        wdg.modify_font(pango.FontDescription(value))

    style_functions = {
        'fg': apply_style_fg,
        'bg': apply_style_bg,
        'font': apply_style_font,
        }

    if style:
        # FIXME: find a better way...
        dummy = gtk.Label()
        dummy.set_style(None)
    
        for name in style:
            style_functions[name](dummy, style[name])
        styles[widget] = dummy.rc_get_style()
    else:
        styles[widget] = None

# This holds all tags for all windows ever    
tag_table = gtk.TextTagTable()

# UI manager to use throughout   
ui_manager = gtk.UIManager()
    
# build our tab widget
window_list = Tabs()

# build our overall UI
ui = UrkUI()
