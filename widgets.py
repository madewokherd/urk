import codecs

import gtk
import pango

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
        
        view.set_style(get_style("nicklist"))
        
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
    
    def get_hover_event(self, hover_iter):
        if not hover_iter.ends_line():
            buffer = self.get_buffer()
            
            line_strt = buffer.get_iter_at_line(hover_iter.get_line())
            line_end = line_strt.copy()
            line_end.forward_lines(1)
            
            pos = hover_iter.get_line_offset()        
            text = buffer.get_text(line_strt, line_end).rstrip("\n")
            
            word, fr, to = word_from_pos(text, pos)
            
            return events.data(
                        window=self.win, pos=pos, text=text,
                        target=word, target_fr=fr, target_to=to,
                        menu=[]
                        )
    
    def mousedown(self, widget, event):
        hover_iter = get_iter_at_event(self, event)

        c_data = self.get_hover_event(hover_iter)
        
        if c_data and event.button == 1:
            events.trigger("Click", c_data)
    
    def mouseup(self, widget, event):
        hover_iter = get_iter_at_event(self, event)

        c_data = self.get_hover_event(hover_iter)
  
        if c_data and event.button == 3:
            events.trigger("RightClick", c_data)
            
            if c_data.menu:
                menu_from_list(c_data.menu).popup(None, None, None, event.button, event.time)
                return True
    
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
    
        buffer = self.get_buffer()

        hover_iter = get_iter_at_event(self, event)

        if not hover_iter.ends_line():        
            line_strt = buffer.get_iter_at_line(hover_iter.get_line())
            line_end = line_strt.copy()
            line_end.forward_lines(1)
            
            pos = hover_iter.get_line_offset()        
            text = line_strt.get_text(line_end).rstrip("\n")
            
            word, fr, to = word_from_pos(text, pos)
            
            h_data = events.data(
                        window=self.win, pos=pos, text=text,
                        target=word, target_fr=fr, target_to=to,
                        tolink=set()
                        )
            events.trigger("Hover", h_data)
            
            offset = line_strt.get_offset()           
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
        
        self.set_style(get_style("view"))
        
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
