import codecs

import gtk
import pango

import conf
import events
import parse_mirc
import ui

HILIT = 4
TEXT = 2
EVENT = 1

# This holds all tags for all windows ever    
tag_table = gtk.TextTagTable()

link_tag = gtk.TextTag('link')
link_tag.set_property('underline',pango.UNDERLINE_SINGLE)
tag_table.add(link_tag)

#FIXME: MEH hates dictionaries, they remind him of the bad words
styles = {}

def style_me(widget, style):
    widget.set_style(styles.get(style))

def set_style(widget, style):
    if style:
        # FIXME: find a better way...
        dummy = gtk.Label()
        dummy.set_style(None)
    
        def apply_style_fg(value):
            dummy.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

        def apply_style_bg(value):
            dummy.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(value))

        def apply_style_font(value):
            dummy.modify_font(pango.FontDescription(value))
    
        style_functions = (
            ('fg', apply_style_fg),
            ('bg', apply_style_bg),
            ('font', apply_style_font),
            )

        for name, f in style_functions:
            if name in style:
                f(style[name])

        style = dummy.rc_get_style()
    
    styles[widget] = style
        
def menu_from_list(alist):
    ui_manager = gtk.UIManager()
    ui_manager.add_ui_from_string('<popup name="Menu"></popup>')
    
    actions = gtk.ActionGroup("Menu")
    
    def callback(action, f): f()
    
    for item in alist: 
        if item:
            if len(item) == 2:
                name, function = item
                action = (name, None, name, None, None, callback)
            elif len(item) == 3:
                name, stock_id, function = item
                action = (name, stock_id, None, None, None, callback)
                
            actions.add_actions([action], function)

            ui_manager.add_ui(ui_manager.new_merge_id(), 
                "/Menu/",
                name, name, 
                gtk.UI_MANAGER_MENUITEM, False)

        else: # None means add a separator
            ui_manager.add_ui(ui_manager.new_merge_id(), 
                "/Menu/",
                "", None, 
                gtk.UI_MANAGER_SEPARATOR, False)
                
    ui_manager.insert_action_group(actions, 0) 
    return ui_manager.get_widget("/Menu")

class Nicklist(gtk.VBox):
    def click(self, widget, event, view):
        if event.button == 3:
            x, y = event.get_coords()
            x, y = int(x), int(y)
    
            (data,), path, x, y = view.get_path_at_pos(x, y)
        
            c_data = events.data(
                        win=self.win,
                        data=data,
                        menu=[]
                        )
        
            events.trigger("ListRightClick", c_data)
            
            if c_data.menu:
                menu_from_list(c_data.menu).popup(None, None, None, event.button, event.time)

    def __init__(self, window):
        gtk.VBox.__init__(self)
        
        self.win = window
        
        self.userlist = gtk.ListStore(str)
        
        view = gtk.TreeView(self.userlist)
        view.set_size_request(0, -1)
        view.set_headers_visible(False)

        view.insert_column_with_attributes(
            0, "", gtk.CellRendererText(), text=0
            )
            
        view.get_column(0).set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        view.set_property("fixed-height-mode", True)
        
        style_me(view, "nicklist")
        
        win = gtk.ScrolledWindow()
        win.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)   
        win.add(view)

        view.connect("button-press-event", self.click, view)

        self.pack_end(win)

# Label used to display/edit your current nick on a network
class NickEdit(gtk.EventBox):
    def update(self, nick=None):
        nick = nick or self.win.network.me
            
        self.label.set_text(nick)
        self.edit.set_text(nick)
    
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
        
        def set_cursor(widget, *args):
            self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))
        
        self.connect("realize", set_cursor)

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
    
    def _set_selection(self, s):
        if s:
            self.select_region(*s)
        else:
            self.select_region(self.cursor, self.cursor)

    #some nice toys for the scriptors
    text = property(gtk.Entry.get_text, gtk.Entry.set_text)
    cursor = property(gtk.Entry.get_position, gtk.Entry.set_position)
    selection=property(gtk.Entry.get_selection_bounds,_set_selection)
    
    def insert(self, text):
        self.do_insert_at_cursor(self, text)
    
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
        tab = gtk.gdk.keyval_from_name("Tab")
        
        eat = set([up, down, tab])
                
        def check_history_explore(widget, event):
            if event.keyval == up:
                widget.history_explore(1)
                
            elif event.keyval == down:
                widget.history_explore(-1)
                
            key = ""
            for k, c in ((gtk.gdk.CONTROL_MASK, '^'),
                            (gtk.gdk.SHIFT_MASK, '!'),
                            (gtk.gdk.MOD1_MASK, '+')):
                if event.state & k:
                    key += c
            
            key += gtk.gdk.keyval_name(event.keyval)
            
            e_data = events.data(key=key,string=event.string,window=self.win)
            
            events.trigger("Keypress", e_data)
            
            return event.keyval in eat

        self.connect("key-press-event", check_history_explore)
        
def prop_to_gtk(prop, val):
    if val == parse_mirc.BOLD:
        return prop, pango.WEIGHT_BOLD

    elif val == parse_mirc.UNDERLINE:
        return prop, pango.UNDERLINE_SINGLE
        
    else:
        return prop, val
        
def word_from_pos(text, pos):
    if text[pos] != " ":
        fr = to = 0
        for word in text.split(" "):
            to += len(word)
            
            if fr <= pos < to:
                break
            
            fr += len(word)
            
            fr += 1
            to += 1

        return word, fr, to
        
    else:
        return "", 0, 0
        
def get_iter_at_event(view, event):
    x, y = event.get_coords()       
    x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(x), int(y))
    
    return view.get_iter_at_location(x, y)

def get_event_at_iter(view, iter):
    buffer = view.get_buffer()
        
    line_strt = buffer.get_iter_at_line(iter.get_line())
    line_end = line_strt.copy()
    line_end.forward_lines(1)
    
    pos = iter.get_line_offset()
    
    #Caveat: text must be a unicode string, not utf-8 encoded; otherwise our
    # offsets will be off when we use anything outside 7-bit ascii
    #gtk.TextIter.get_text returns unicode but gtk.TextBuffer.get_text does not
    text = line_strt.get_text(line_end).rstrip("\n")
    
    word, fr, to = word_from_pos(text, pos)
    
    return events.data(
                window=view.win, pos=pos, text=text,
                target=word, target_fr=fr, target_to=to,
                )

class TextOutput(gtk.TextView):
    # the unknowing print weird things to our text widget function
    def write(self, text, activity_type=EVENT):
        if not isinstance(text, unicode):
            try:
                text = codecs.utf_8_decode(text)[0]
            except:
                text = codecs.latin_1_decode(text)[0]
        tag_data, text = parse_mirc.parse_mirc(text)
    
        buffer = self.get_buffer()
        
        cc, end = buffer.get_char_count(), buffer.get_end_iter()
        
        end_rect, vis_rect = self.get_iter_location(end), self.get_visible_rect()
        
        # this means we're scrolled down right to the bottom
        # we interpret this to mean we should scroll down after we've
        # inserted more text into the buffer
        if end_rect.y + end_rect.height <= vis_rect.y + vis_rect.height:
            def scroll():
                self.scroll_mark_onscreen(buffer.get_mark("end"))
                
            ui.register_idle(scroll)

        buffer.insert(end, text + "\n")

        for tag_props, start_i, end_i in tag_data:
            tag_props = tuple(prop_to_gtk(*p) for p in tag_props)
            tag_name = str(hash(tag_props))
                 
            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **dict(tag_props))
                
            buffer.apply_tag_by_name(
                tag_name, 
                buffer.get_iter_at_offset(start_i + cc),
                buffer.get_iter_at_offset(end_i + cc)
                )
    
    def mousedown(self, widget, event):
        if event.button == 3:
            hover_iter = get_iter_at_event(self, event)
            
            if not hover_iter.ends_line():
                c_data = get_event_at_iter(self, hover_iter)
                c_data.menu = []

                events.trigger("RightClick", c_data)
            
                if c_data.menu:
                    menu_from_list(c_data.menu).popup(None, None, None, event.button, event.time)
                    return True
    
    def mouseup(self, widget, event):
        if event.button == 1 and not self.get_buffer().get_selection_bounds():
            hover_iter = get_iter_at_event(self, event)
        
            if not hover_iter.ends_line():
                c_data = get_event_at_iter(self, hover_iter)

                events.trigger("Click", c_data)

    def clear_hover(self, *args):
        buffer = self.get_buffer()
    
        for fr, to in self.linking:
            buffer.remove_tag_by_name(
                "link", 
                buffer.get_iter_at_mark(fr), 
                buffer.get_iter_at_mark(to)
                )
        
        self.linking = set()
        self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)

    def hover(self, widget, event):
        self.clear_hover()

        hover_iter = get_iter_at_event(self, event)

        if not hover_iter.ends_line():        
            h_data = get_event_at_iter(self, hover_iter)
            h_data.tolink = set()

            events.trigger("Hover", h_data)
            
            if h_data.tolink:
                buffer = self.get_buffer()
            
                offset = buffer.get_iter_at_line(hover_iter.get_line()).get_offset()        
                for fr, to in h_data.tolink:
                    fr = buffer.get_iter_at_offset(offset + fr)
                    to = buffer.get_iter_at_offset(offset + to)
                    
                    buffer.apply_tag_by_name("link", fr, to)
                    
                    self.linking.add(
                        (buffer.create_mark(None, fr), 
                            buffer.create_mark(None, to))
                        )
                        
                    self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))

        self.get_pointer()

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

        self.linking = set()
        
        # self.props.events |= gtk.gdk.POINTER_MOTION_HINT_MASK  (pygtk 2.8)
        self.set_property("events", 
            self.get_property("events") | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.LEAVE_NOTIFY_MASK
            )
        
        self.connect("motion-notify-event", self.hover)
        self.connect("button-press-event", self.mousedown)
        self.connect("button-release-event", self.mouseup)
        self.connect("leave-notify-event", self.clear_hover)
        
        style_me(self, "view")
        
        def set_cursor(widget):
            self.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(None)      

        self.connect("realize", set_cursor)

class WindowLabel(gtk.EventBox):
    def update(self):
        activity_markup = {
            HILIT: "<span style='italic' foreground='#00F'>%s</span>",
            TEXT: "<span foreground='red'>%s</span>",
            EVENT: "<span foreground='#363'>%s</span>",
            }
            
        title = str(self)
    
        for a_type in (HILIT, TEXT, EVENT):
            if self.win.activity & a_type:
                title = activity_markup[a_type] % title
                break
            
        self.label.set_markup(title)

    def tab_popup(self, widget, event):
        if event.button == 3: # right click
            c_data = events.data(window=self.win, menu=[])
            events.trigger("WindowMenu", c_data)
            
            c_data.menu += [None, ("Close", gtk.STOCK_CLOSE, self.win.close)]
            
            menu_from_list(c_data.menu).popup(None, None, None, event.button, event.time)
            
    def __str__(self):
        return self.win.get_title()

    def __init__(self, window):
        gtk.EventBox.__init__(self)

        self.win = window
        self.connect("button-press-event", self.tab_popup)
        
        self.label = gtk.Label()        
        self.add(self.label)
        
        self.update()
        
class WindowLedge(gtk.VBox):
    def __init__(self, window):
        gtk.VBox.__init__(self)
        self.child = window
        
        self.add(self.child)
        self.show()
        
class WindowListTabs(gtk.Notebook):
    def get_active(self):
        return self.get_nth_page(self.get_current_page()).child
        
    def set_active(self, window):
        for window_ledge in self:
            if window_ledge.child is window:
                self.set_current_page(self.page_num(window_ledge))
                break
       
    def add(self, window):
        pos = self.get_n_pages()
        if window.network:
            for i in reversed(range(pos)):
                if self.get_nth_page(i).child.network == window.network:
                    pos = i+1
                    break
                    
        wbox = WindowLedge(window)

        self.insert_page(wbox, None, pos)
        self.set_tab_label(wbox, window.title)
        
    def remove(self, window):
        for window_ledge in self:
            if window_ledge.child is window:
                self.remove_page(self.page_num(window_ledge))
                break
        
    def swap(self, window1, window2):
        for window_ledge in self:
            if window_ledge.child is window1:
                window_ledge.remove(window1)
                
                window_ledge.child = window2
                window_ledge.add(window_ledge.child)
                
                self.set_tab_label(window_ledge, window2.title)
                
                ui.register_idle(window2.focus)
                
                break

    def __init__(self):
        gtk.Notebook.__init__(self)
        
        tab_pos = conf.get("ui-gtk/tab-pos")
        if tab_pos is not None:
            self.set_property("tab-pos", tab_pos)
        else:
            self.set_property("tab-pos", gtk.POS_TOP)

        self.set_scrollable(True)
        
        def window_change(self, wptr, page_num):
            events.trigger("Active", self.get_nth_page(page_num).child)
        self.connect("switch-page", window_change)
    
    def __iter__(self):
        return iter(self.get_children())
    
"""class WindowListButtons(gtk.HBox):
    def get_active(self):
        if self.windows.get_children():
            return self.windows.get_children()[0]
        
    def set_active(self, window):
        if window != self.get_active():
            if self.windows.get_children():
                self.windows.remove(self.windows.get_children()[0])
            self.windows.add(window)
            
            events.trigger("Active", window)
       
    def add(self, window):
        def activate_window(widget, event):
            if event.button == 1:
                self.set_active(window)
        window.title.connect("button-press-event", activate_window)
        
        self.buttons.add(window.title)
        self.manager[window] = window.title
        
    def remove(self, window):
        self.buttons.remove(self.manager[window])
        self.windows.remove(window)
        del self.manager[window]

    def __init__(self):
        gtk.HBox.__init__(self)
        
        self.manager = {}
        
        self.buttons = gtk.VButtonBox()
        self.buttons.set_layout(gtk.BUTTONBOX_START)

        self.windows = gtk.VBox()
        
        self.pack_start(self.buttons, expand=False)
        self.pack_end(self.windows, expand=True)"""
