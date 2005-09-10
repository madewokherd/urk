import gtk
import pango

import events
import parse_mirc
import ui

# FIXME: make these the same as ui
# Window activity Constants
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
                
            ui.register_idle(scroll)

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
            
    def click(self, widget, event):
        buffer = self.get_buffer()
    
        x, y = event.get_coords()       
        x, y = self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(x), int(y))
    
        hover_iter = self.get_iter_at_location(x, y)

        if not hover_iter.ends_line():
            line_strt = buffer.get_iter_at_line(hover_iter.get_line())
            line_end = line_strt.copy()
            line_end.forward_lines(1)
            
            pos = hover_iter.get_line_offset()        
            text = buffer.get_text(line_strt, line_end).rstrip("\n")
            
            fr = to = 0
            for word in text.split(" "):
                to += len(word)
                
                if fr <= pos < to:
                    break
                
                fr += len(word)
                
                fr += 1
                to += 1
            else:
                word = ""
            
            h_data = events.data(
                        window=self.win, pos=pos, text=text,
                        word=word, word_fr=fr, word_to=to,
                        tolink=set()
                        )
            events.trigger("Hover", h_data)
    
    def clear_hover(self, *args):
        buffer = self.get_buffer()
    
        for fr, to in self.linking:
            buffer.remove_tag_by_name("link", fr, to)
        
        self.linking = set()

    def hover(self, widget, event):
        self.clear_hover()
    
        buffer = self.get_buffer()

        x, y = event.get_coords()
        x, y = self.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, int(x), int(y))
    
        hover_iter = self.get_iter_at_location(x, y)

        if not hover_iter.ends_line():
            line_strt = buffer.get_iter_at_line(hover_iter.get_line())
            line_end = line_strt.copy()
            line_end.forward_lines(1)
            
            pos = hover_iter.get_line_offset()        
            text = buffer.get_text(line_strt, line_end).rstrip("\n")
            
            fr = to = 0
            for word in text.split(" "):
                to += len(word)
                
                if fr <= pos < to:
                    break
                
                fr += len(word)
                
                fr += 1
                to += 1
            else:
                word = ""
            
            h_data = events.data(
                        window=self.win, pos=pos, text=text,
                        word=word, word_fr=fr, word_to=to,
                        tolink=set()
                        )
            events.trigger("Hover", h_data)
            
            offset = line_strt.get_offset()           
            for fr, to in h_data.tolink:
                fr = buffer.get_iter_at_offset(offset + fr)
                to = buffer.get_iter_at_offset(offset + to)
                
                buffer.apply_tag_by_name("link", fr, to)
                
                self.linking.add((fr, to))

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
        self.connect("button-press-event", self.click)
        self.connect("leave-notify-event", self.clear_hover)
        
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
            c_data = events.data(window=self.win, menu=[])
            events.trigger("WindowMenu", c_data)

            ui_manager = gtk.UIManager()
            ui_manager.add_ui_from_string('<popup name="TabPopup"></popup>')
            
            actions = gtk.ActionGroup("Tab")
            
            def callback(action, f): f()
            
            for item in c_data.menu: 
                if item:
                    name, function = item
                        
                    actions.add_actions(
                        ((name, None, name, None, None, callback),), function
                        )

                    ui_manager.add_ui(ui_manager.new_merge_id(), 
                        "/TabPopup/",
                        name, name, 
                        gtk.UI_MANAGER_MENUITEM, False)

                else: # None means add a separator
                    ui_manager.add_ui(ui_manager.new_merge_id(), 
                        "/TabPopup/",
                        "", None, 
                        gtk.UI_MANAGER_SEPARATOR, False)

            actions.add_actions(
                (("Close", gtk.STOCK_CLOSE, None, "<Control>W", None, callback),),
                self.win.close
                )
             
            ui_manager.add_ui(ui_manager.new_merge_id(), 
                        "/TabPopup/",
                        "", None, 
                        gtk.UI_MANAGER_SEPARATOR, False)   
            ui_manager.add_ui(ui_manager.new_merge_id(), 
                        "/TabPopup/",
                        "Close", "Close", 
                        gtk.UI_MANAGER_MENUITEM, False)
                        
            ui_manager.insert_action_group(actions, 0) 
            ui_manager.get_widget(
                "/TabPopup"
                ).popup(None, None, None, event.button, event.time)

    def __init__(self, window):
        gtk.EventBox.__init__(self)

        self.win = window
        self.connect("button-press-event", self.tab_popup)
        
        self.label = gtk.Label()        
        self.add(self.label)
        
        self.update()